"""
Analyzer — main orchestrator that runs all checks and produces a RugReport.
"""

import asyncio
import time
from src.models import RugReport, TokenMetadata, score_to_risk
from src.chain_scanner import ChainScanner
from src.creator_checker import CreatorChecker
from src.bundle_detector import BundleDetector
from src.social_checker import SocialChecker
from src.ai_scorer import AIScorer
from src.logger import get_logger

logger = get_logger(__name__)


class Analyzer:
    def __init__(self):
        self.chain = ChainScanner()
        self.creator_checker = CreatorChecker()
        self.bundle_detector = BundleDetector()
        self.social_checker = SocialChecker()
        self.ai_scorer = AIScorer()

    async def analyze(
        self,
        mint: str,
        name: str = "",
        symbol: str = "",
        description: str = "",
        twitter: str = "",
        telegram: str = "",
        website: str = "",
        creator: str = "",
        market_cap_sol: float = 0.0,
        created_at: int | None = None,
    ) -> RugReport:
        """
        Run all RugRadar checks on a token and return a full RugReport.

        Parameters:
        - mint: Token mint address
        - name, symbol, description: Token metadata
        - twitter, telegram, website: Social links
        - creator: Creator wallet address
        - market_cap_sol: Current market cap in SOL
        - created_at: Unix timestamp of token creation

        Returns:
        - RugReport with all check results and Trust Score
        """
        age_seconds = 0
        if created_at:
            age_seconds = int(time.time()) - created_at

        metadata = TokenMetadata(
            mint=mint,
            name=name or "Unknown",
            symbol=symbol or "???",
            description=description,
            twitter=twitter,
            telegram=telegram,
            website=website,
            creator=creator,
            created_at=created_at,
            market_cap_sol=market_cap_sol,
            age_seconds=age_seconds,
        )

        report = RugReport(metadata=metadata)

        logger.info(f"Running RugRadar checks on {name} ({mint[:12]}...)")

        # Run independent checks concurrently
        (
            report.mint_check,
            report.holder_check,
            report.liquidity_check,
            report.creator_check,
            report.bundle_check,
            report.social_check,
        ) = await asyncio.gather(
            self.chain.check_mint_authority(mint),
            self.chain.check_holders(mint),
            self.chain.check_liquidity(mint),
            self.creator_checker.check_creator(creator) if creator else asyncio.coroutine(lambda: __import__('src.models', fromlist=['CreatorCheck']).CreatorCheck())(),
            self.bundle_detector.detect_bundles(mint),
            self.social_checker.check_socials(twitter, telegram, website),
        )

        logger.info(f"Raw score: {report.calculate_raw_score()}/100 — running AI synthesis...")

        # AI synthesis (sequential, depends on all checks)
        report = await self.ai_scorer.synthesize(report)
        report.risk_level = score_to_risk(report.trust_score)

        logger.info(
            f"Analysis complete: {name} → Trust Score {report.trust_score}/100 [{report.risk_level.value}]"
        )
        return report
