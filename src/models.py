from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    LIKELY_RUG = "LIKELY_RUG"


RISK_COLORS = {
    RiskLevel.SAFE: "bold green",
    RiskLevel.LOW_RISK: "green",
    RiskLevel.MEDIUM_RISK: "yellow",
    RiskLevel.HIGH_RISK: "bold red",
    RiskLevel.LIKELY_RUG: "bold red on black",
}

RISK_EMOJIS = {
    RiskLevel.SAFE: "✅",
    RiskLevel.LOW_RISK: "🟢",
    RiskLevel.MEDIUM_RISK: "🟡",
    RiskLevel.HIGH_RISK: "🔴",
    RiskLevel.LIKELY_RUG: "💀",
}


def score_to_risk(score: int) -> RiskLevel:
    if score >= 80:
        return RiskLevel.SAFE
    elif score >= 65:
        return RiskLevel.LOW_RISK
    elif score >= 45:
        return RiskLevel.MEDIUM_RISK
    elif score >= 25:
        return RiskLevel.HIGH_RISK
    else:
        return RiskLevel.LIKELY_RUG


@dataclass
class MintAuthorityCheck:
    mint_authority_active: bool = False
    freeze_authority_active: bool = False
    supply: int = 0
    decimals: int = 6
    score: int = 25  # Max 25 points

    def to_dict(self) -> dict:
        return {
            "mint_authority_active": self.mint_authority_active,
            "freeze_authority_active": self.freeze_authority_active,
            "supply": self.supply,
            "decimals": self.decimals,
            "score": self.score,
        }


@dataclass
class HolderCheck:
    top_holders: list[dict] = field(default_factory=list)
    top10_concentration_pct: float = 0.0
    total_holders: int = 0
    score: int = 20  # Max 20 points

    def to_dict(self) -> dict:
        return {
            "top_holders": self.top_holders[:5],
            "top10_concentration_pct": round(self.top10_concentration_pct, 2),
            "total_holders": self.total_holders,
            "score": self.score,
        }


@dataclass
class CreatorCheck:
    creator_address: str = ""
    tokens_created: int = 0
    tokens_abandoned: int = 0
    wallet_age_days: int = 0
    known_rugger: bool = False
    score: int = 20  # Max 20 points

    def to_dict(self) -> dict:
        return {
            "creator_address": self.creator_address,
            "tokens_created": self.tokens_created,
            "tokens_abandoned": self.tokens_abandoned,
            "wallet_age_days": self.wallet_age_days,
            "known_rugger": self.known_rugger,
            "score": self.score,
        }


@dataclass
class BundleCheck:
    bundle_detected: bool = False
    wallets_in_bundle: int = 0
    bundle_sol_amount: float = 0.0
    score: int = 15  # Max 15 points

    def to_dict(self) -> dict:
        return {
            "bundle_detected": self.bundle_detected,
            "wallets_in_bundle": self.wallets_in_bundle,
            "bundle_sol_amount": round(self.bundle_sol_amount, 4),
            "score": self.score,
        }


@dataclass
class SocialCheck:
    has_twitter: bool = False
    has_telegram: bool = False
    has_website: bool = False
    twitter_reachable: bool = False
    website_reachable: bool = False
    score: int = 10  # Max 10 points

    def to_dict(self) -> dict:
        return {
            "has_twitter": self.has_twitter,
            "has_telegram": self.has_telegram,
            "has_website": self.has_website,
            "twitter_reachable": self.twitter_reachable,
            "website_reachable": self.website_reachable,
            "score": self.score,
        }


@dataclass
class LiquidityCheck:
    liquidity_sol: float = 0.0
    lp_burned: bool = False
    lp_locked: bool = False
    graduated_to_raydium: bool = False
    score: int = 10  # Max 10 points

    def to_dict(self) -> dict:
        return {
            "liquidity_sol": round(self.liquidity_sol, 4),
            "lp_burned": self.lp_burned,
            "lp_locked": self.lp_locked,
            "graduated_to_raydium": self.graduated_to_raydium,
            "score": self.score,
        }


@dataclass
class TokenMetadata:
    mint: str = ""
    name: str = ""
    symbol: str = ""
    description: str = ""
    image_uri: str = ""
    twitter: str = ""
    telegram: str = ""
    website: str = ""
    creator: str = ""
    created_at: Optional[int] = None
    market_cap_sol: float = 0.0
    age_seconds: int = 0


@dataclass
class RugReport:
    metadata: TokenMetadata = field(default_factory=TokenMetadata)
    mint_check: MintAuthorityCheck = field(default_factory=MintAuthorityCheck)
    holder_check: HolderCheck = field(default_factory=HolderCheck)
    creator_check: CreatorCheck = field(default_factory=CreatorCheck)
    bundle_check: BundleCheck = field(default_factory=BundleCheck)
    social_check: SocialCheck = field(default_factory=SocialCheck)
    liquidity_check: LiquidityCheck = field(default_factory=LiquidityCheck)

    trust_score: int = 0
    risk_level: RiskLevel = RiskLevel.HIGH_RISK
    ai_verdict: str = ""
    ai_reasoning: str = ""
    red_flags: list[str] = field(default_factory=list)
    positives: list[str] = field(default_factory=list)

    def calculate_raw_score(self) -> int:
        return (
            self.mint_check.score +
            self.holder_check.score +
            self.creator_check.score +
            self.bundle_check.score +
            self.social_check.score +
            self.liquidity_check.score
        )

    def to_dict(self) -> dict:
        return {
            "mint": self.metadata.mint,
            "name": self.metadata.name,
            "symbol": self.metadata.symbol,
            "trust_score": self.trust_score,
            "risk_level": self.risk_level.value,
            "ai_verdict": self.ai_verdict,
            "ai_reasoning": self.ai_reasoning,
            "red_flags": self.red_flags,
            "positives": self.positives,
            "checks": {
                "mint_authority": self.mint_check.to_dict(),
                "holders": self.holder_check.to_dict(),
                "creator": self.creator_check.to_dict(),
                "bundle": self.bundle_check.to_dict(),
                "socials": self.social_check.to_dict(),
                "liquidity": self.liquidity_check.to_dict(),
            }
        }
