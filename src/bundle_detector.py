"""
BundleDetector — detects coordinated buying (bundling) at token launch.

Bundling = multiple wallets buying in the same block/transaction batch.
This is a classic insider manipulation technique where the team
pre-buys large amounts before the token goes public.
"""

import aiohttp
import asyncio
from collections import defaultdict
from src.models import BundleCheck
from src.logger import get_logger
from config import config

logger = get_logger(__name__)


class BundleDetector:
    def __init__(self):
        self.rpc_url = config.SOLANA_RPC_URL
        self.helius_key = config.HELIUS_API_KEY

    async def _get_early_transactions(self, mint: str) -> list[dict]:
        """Get earliest transactions for this token mint."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [mint, {"limit": 50}]
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
                        return data.get("result", [])
        except Exception as e:
            logger.debug(f"Bundle detection RPC error: {e}")
        return []

    async def _get_transaction_detail(self, sig: str) -> dict | None:
        """Get full transaction details including slot and accounts."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("result")
        except Exception:
            pass
        return None

    async def detect_bundles(self, mint: str) -> BundleCheck:
        """
        Detect bundle buying in the first blocks after token creation.

        Methodology:
        1. Get earliest 20 transactions for the mint
        2. Group by slot (block)
        3. If multiple unique wallets bought in the same slot = bundle
        """
        check = BundleCheck()

        txs = await self._get_early_transactions(mint)
        if not txs:
            check.score = 10  # Unknown, partial penalty
            return check

        # Analyze first 20 transactions
        early_txs = txs[:20]

        # Group transactions by slot
        slot_wallets: dict[int, list[str]] = defaultdict(list)
        slot_amounts: dict[int, float] = defaultdict(float)

        tasks = [self._get_transaction_detail(tx["signature"]) for tx in early_txs[:10]]
        details = await asyncio.gather(*tasks, return_exceptions=True)

        for detail in details:
            if isinstance(detail, Exception) or detail is None:
                continue
            try:
                slot = detail.get("slot", 0)
                message = detail.get("transaction", {}).get("message", {})
                account_keys = message.get("accountKeys", [])

                # Extract fee payer (buyer) — first account
                if account_keys:
                    buyer = account_keys[0].get("pubkey", "") if isinstance(account_keys[0], dict) else account_keys[0]
                    if buyer:
                        slot_wallets[slot].append(buyer)

                # Try to extract SOL amount from pre/post balances
                pre = detail.get("meta", {}).get("preBalances", [0])
                post = detail.get("meta", {}).get("postBalances", [0])
                if pre and post:
                    sol_moved = abs(pre[0] - post[0]) / 1e9
                    slot_amounts[slot] += sol_moved

            except Exception:
                continue

        # Find slots with multiple unique buyers
        max_bundle_size = 0
        total_bundle_sol = 0.0
        bundle_detected = False

        for slot, wallets in slot_wallets.items():
            unique_wallets = len(set(wallets))
            if unique_wallets >= 3:
                bundle_detected = True
                if unique_wallets > max_bundle_size:
                    max_bundle_size = unique_wallets
                total_bundle_sol += slot_amounts.get(slot, 0)

        check.bundle_detected = bundle_detected
        check.wallets_in_bundle = max_bundle_size
        check.bundle_sol_amount = total_bundle_sol

        # Score: 15 max
        score = 15
        if bundle_detected:
            if max_bundle_size >= 10:
                score -= 15  # Massive bundle
            elif max_bundle_size >= 5:
                score -= 10
            elif max_bundle_size >= 3:
                score -= 6
        check.score = max(0, score)
        return check
