"""
AIScorer — uses GPT to synthesize all check results into a final verdict.

The AI doesn't replace the rule-based checks — it synthesizes them.
It adds context, spots patterns humans might miss, and explains the verdict.
"""

import json
from openai import AsyncOpenAI
from src.models import RugReport
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

SYNTHESIS_PROMPT = """You are RugRadar, an expert AI system specializing in Solana token security analysis and rug pull detection.

You have already run 6 automated checks on this token. Your job is to:
1. Synthesize the check results into a final verdict
2. Identify the most critical red flags
3. Highlight any positives
4. Provide a final Trust Score adjustment (within ±10 of the raw score)

Respond ONLY with valid JSON in this exact format:
{
  "trust_score": <0-100>,
  "verdict": "<SAFE|LOW_RISK|MEDIUM_RISK|HIGH_RISK|LIKELY_RUG>",
  "reasoning": "<2-3 clear sentences explaining the verdict>",
  "red_flags": ["<flag1>", "<flag2>", "<flag3>"],
  "positives": ["<positive1>", "<positive2>"]
}

Verdict thresholds:
- SAFE (80-100): Multiple positive signals, no major red flags
- LOW_RISK (65-79): Minor concerns, mostly positive
- MEDIUM_RISK (45-64): Notable concerns, proceed with caution
- HIGH_RISK (25-44): Serious red flags present
- LIKELY_RUG (0-24): Multiple critical red flags, very likely a rug pull

Raw score from automated checks: {raw_score}/100

Token data and check results:
{check_data}
"""


class AIScorer:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    async def synthesize(self, report: RugReport) -> RugReport:
        """
        Use GPT to synthesize all check results and produce a final Trust Score.

        Modifies the report in-place and returns it.
        """
        raw_score = report.calculate_raw_score()

        check_data = {
            "token": {
                "name": report.metadata.name,
                "symbol": report.metadata.symbol,
                "description": report.metadata.description[:300],
                "age_seconds": report.metadata.age_seconds,
                "market_cap_sol": report.metadata.market_cap_sol,
            },
            "mint_authority": report.mint_check.to_dict(),
            "holders": report.holder_check.to_dict(),
            "creator": report.creator_check.to_dict(),
            "bundle": report.bundle_check.to_dict(),
            "socials": report.social_check.to_dict(),
            "liquidity": report.liquidity_check.to_dict(),
        }

        prompt = SYNTHESIS_PROMPT.format(
            raw_score=raw_score,
            check_data=json.dumps(check_data, indent=2)
        )

        try:
            response = await self.client.chat.completions.create(
                model=config.GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.GPT_MAX_TOKENS,
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            report.trust_score = max(0, min(100, result.get("trust_score", raw_score)))
            report.ai_verdict = result.get("verdict", "HIGH_RISK")
            report.ai_reasoning = result.get("reasoning", "Analysis failed.")
            report.red_flags = result.get("red_flags", [])
            report.positives = result.get("positives", [])

        except Exception as e:
            logger.error(f"AI scoring failed: {e}")
            # Fallback to raw score without AI synthesis
            report.trust_score = raw_score
            report.ai_verdict = "HIGH_RISK"
            report.ai_reasoning = "AI analysis unavailable. Using automated checks only."
            report.red_flags = []
            report.positives = []

        return report
