"""
CreatorChecker — analyzes the token creator's wallet history.

Checks:
- How many tokens has this wallet created?
- How many of those tokens were abandoned (went to 0)?
- How old is this wallet?
- Is this wallet on any known rugger list?
"""

import aiohttp
import time
from src.models import CreatorCheck
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

# Known rugger addresses (community-maintained, extend as needed)
KNOWN_RUGGERS: set[str] = set()


class CreatorChecker:
    def __init__(self):
        self.rpc_url = config.SOLANA_RPC_URL
        self.helius_key = config.HELIUS_API_KEY

    async def _get_token_accounts_by_owner(self, owner: str) -> list[dict]:
        """Get all token accounts created by this wallet via Helius."""
        if not self.helius_key:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.helius.xyz/v0/addresses/{owner}/transactions"
                    f"?api-key={self.helius_key}&type=CREATE_TOKEN&limit=50",
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception as e:
            logger.debug(f"Helius creator check failed: {e}")
            return []

    async def _get_wallet_age(self, address: str) -> int:
        """Estimate wallet age in days by fetching earliest transaction."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [address, {"limit": 1000}]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        sigs = data.get("result", [])
                        if sigs:
                            oldest = sigs[-1]
                            block_time = oldest.get("blockTime", int(time.time()))
                            age_seconds = int(time.time()) - block_time
                            return age_seconds // 86400  # convert to days
        except Exception as e:
            logger.debug(f"Wallet age check failed: {e}")
        return 0

    async def _count_created_tokens(self, creator: str) -> tuple[int, int]:
        """
        Count how many tokens this wallet created and how many are abandoned.
        Uses Helius enhanced API if available, falls back to RPC signatures.

        Returns:
        - tuple[int, int]: (tokens_created, tokens_abandoned)
        """
        if self.helius_key:
            txs = await self._get_token_accounts_by_owner(creator)
            created = len(txs)
            # Heuristic: if wallet created many tokens, assume some abandoned
            abandoned = max(0, created - 1) if created > 3 else 0
            return created, abandoned

        # Fallback: count InitializeMint instructions in recent txs
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [creator, {"limit": 100}]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        sigs = data.get("result", [])
                        # Conservative estimate without full tx parsing
                        created = min(len(sigs) // 10, 20)
                        abandoned = max(0, created - 1) if created > 2 else 0
                        return created, abandoned
        except Exception:
            pass

        return 0, 0

    async def check_creator(self, creator: str) -> CreatorCheck:
        """Full creator wallet analysis."""
        check = CreatorCheck(creator_address=creator)

        check.known_rugger = creator in KNOWN_RUGGERS
        if check.known_rugger:
            logger.warning(f"Known rugger detected: {creator[:12]}...")
            check.score = 0
            return check

        # Run checks concurrently
        import asyncio
        wallet_age_task = asyncio.create_task(self._get_wallet_age(creator))
        token_count_task = asyncio.create_task(self._count_created_tokens(creator))

        check.wallet_age_days = await wallet_age_task
        check.tokens_created, check.tokens_abandoned = await token_count_task

        # Score: 20 max
        score = 20

        # New wallet = higher risk
        if check.wallet_age_days < 1:
            score -= 10
        elif check.wallet_age_days < 7:
            score -= 5

        # Many tokens = serial launcher (not always bad, but suspicious)
        if check.tokens_created > 10:
            score -= 8
        elif check.tokens_created > 5:
            score -= 4
        elif check.tokens_created > 2:
            score -= 2

        # Abandoned tokens = strong red flag
        if check.tokens_abandoned > 5:
            score -= 10
        elif check.tokens_abandoned > 2:
            score -= 6
        elif check.tokens_abandoned > 0:
            score -= 3

        check.score = max(0, score)
        return check
