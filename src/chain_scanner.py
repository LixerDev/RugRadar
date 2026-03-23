"""
ChainScanner — fetches on-chain data via Solana JSON-RPC.

Checks:
- Mint authority status (can creator mint more?)
- Freeze authority status (can creator freeze wallets?)
- Token supply and decimals
- Top token holders and concentration
"""

import aiohttp
import json
import time
from src.models import MintAuthorityCheck, HolderCheck, LiquidityCheck
from src.logger import get_logger
from config import config

logger = get_logger(__name__)


class ChainScanner:
    def __init__(self):
        self.rpc_url = config.SOLANA_RPC_URL
        self.helius_key = config.HELIUS_API_KEY

    async def _rpc_call(self, method: str, params: list) -> dict | None:
        """Make a Solana JSON-RPC call."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
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
                        return data.get("result")
                    else:
                        logger.warning(f"RPC call {method} failed: HTTP {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"RPC call error ({method}): {e}")
            return None

    async def check_mint_authority(self, mint: str) -> MintAuthorityCheck:
        """
        Check if mint authority and freeze authority are still active.
        Both being active are major red flags — means creator has full control.
        """
        result = await self._rpc_call("getAccountInfo", [
            mint,
            {"encoding": "jsonParsed"}
        ])

        check = MintAuthorityCheck()

        if not result or not result.get("value"):
            logger.warning(f"Could not fetch mint info for {mint}")
            check.score = 10  # Unknown = some penalty
            return check

        try:
            info = result["value"]["data"]["parsed"]["info"]
            mint_auth = info.get("mintAuthority")
            freeze_auth = info.get("freezeAuthority")
            check.supply = int(info.get("supply", 0))
            check.decimals = info.get("decimals", 6)

            check.mint_authority_active = mint_auth is not None
            check.freeze_authority_active = freeze_auth is not None

            # Score: 25 max
            # -15 if mint authority active (can create unlimited tokens)
            # -10 if freeze authority active (can freeze your tokens)
            score = 25
            if check.mint_authority_active:
                score -= 15
            if check.freeze_authority_active:
                score -= 10
            check.score = max(0, score)

        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to parse mint info: {e}")
            check.score = 10

        return check

    async def check_holders(self, mint: str) -> HolderCheck:
        """
        Fetch top token holders and calculate concentration.
        High concentration (>60% in top 10) = dump risk.
        """
        result = await self._rpc_call("getTokenLargestAccounts", [mint])
        check = HolderCheck()

        if not result or not result.get("value"):
            logger.warning(f"Could not fetch holders for {mint}")
            check.score = 10
            return check

        try:
            accounts = result["value"][:config.MAX_HOLDERS_TO_FETCH]
            if not accounts:
                check.score = 5
                return check

            total_supply_result = await self._rpc_call("getAccountInfo", [
                mint, {"encoding": "jsonParsed"}
            ])
            total_supply = 1
            if total_supply_result and total_supply_result.get("value"):
                info = total_supply_result["value"]["data"]["parsed"]["info"]
                total_supply = int(info.get("supply", 1))
                decimals = info.get("decimals", 6)
                total_supply_adjusted = total_supply / (10 ** decimals)
            else:
                total_supply_adjusted = total_supply

            holders = []
            top10_total = 0.0
            for acc in accounts[:10]:
                amount = float(acc.get("uiAmount", 0) or 0)
                pct = (amount / total_supply_adjusted * 100) if total_supply_adjusted > 0 else 0
                holders.append({
                    "address": acc.get("address", ""),
                    "amount": round(amount, 2),
                    "percentage": round(pct, 2)
                })
                top10_total += pct

            check.top_holders = holders
            check.top10_concentration_pct = round(top10_total, 2)
            check.total_holders = len(accounts)

            # Score: 20 max
            # Deduct based on concentration
            score = 20
            if top10_total > 80:
                score -= 15
            elif top10_total > 60:
                score -= 10
            elif top10_total > 40:
                score -= 5
            check.score = max(0, score)

        except Exception as e:
            logger.error(f"Error analyzing holders: {e}")
            check.score = 8

        return check

    async def check_liquidity(self, mint: str) -> LiquidityCheck:
        """
        Check liquidity status for a PumpFun token.
        On PumpFun: LP is burned when token graduates to Raydium.
        Burned LP = safer. Unlocked LP = creator can remove it anytime.
        """
        check = LiquidityCheck()

        # For PumpFun tokens, we check if it has graduated to Raydium
        # by looking for a Raydium pool account
        # This is a simplified check — production would use Birdeye/Helius
        try:
            if config.BIRDEYE_API_KEY:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://public-api.birdeye.so/defi/token_overview?address={mint}",
                        headers={"X-API-KEY": config.BIRDEYE_API_KEY},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            token_data = data.get("data", {})
                            check.liquidity_sol = float(token_data.get("liquidity", 0))
                            check.graduated_to_raydium = check.liquidity_sol > 85
                            check.lp_burned = check.graduated_to_raydium
            else:
                # Without Birdeye, use heuristic: assume PumpFun token LP not yet burned
                check.lp_burned = False
                check.lp_locked = False

            # Score: 10 max
            score = 10
            if not check.lp_burned and not check.lp_locked:
                score -= 5
            if check.liquidity_sol < 10:
                score -= 3
            check.score = max(0, score)

        except Exception as e:
            logger.warning(f"Liquidity check failed: {e}")
            check.score = 5

        return check
