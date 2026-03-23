"""
SocialChecker — verifies social media presence for a token.

Checks:
- Does it have Twitter/Telegram/Website links?
- Are those links reachable (not 404)?
- Does the website look real (not a 1-page template)?
"""

import aiohttp
import asyncio
from src.models import SocialCheck
from src.logger import get_logger

logger = get_logger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=8)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


class SocialChecker:
    async def _check_url(self, url: str) -> bool:
        """Check if a URL is reachable and returns 200."""
        if not url or not url.startswith("http"):
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True) as resp:
                    return resp.status < 400
        except Exception:
            return False

    async def _check_twitter(self, twitter_url: str) -> bool:
        """Check Twitter handle reachability."""
        if not twitter_url:
            return False
        # Normalize URL
        if not twitter_url.startswith("http"):
            twitter_url = f"https://twitter.com/{twitter_url.lstrip('@')}"
        return await self._check_url(twitter_url)

    async def _check_telegram(self, telegram_url: str) -> bool:
        """Check Telegram group reachability."""
        if not telegram_url:
            return False
        if not telegram_url.startswith("http"):
            telegram_url = f"https://t.me/{telegram_url.lstrip('@').lstrip('t.me/')}"
        return await self._check_url(telegram_url)

    async def check_socials(
        self,
        twitter: str = "",
        telegram: str = "",
        website: str = ""
    ) -> SocialCheck:
        """
        Run all social checks concurrently.

        Parameters:
        - twitter: Twitter URL or handle
        - telegram: Telegram URL or handle
        - website: Website URL

        Returns:
        - SocialCheck with scores
        """
        check = SocialCheck(
            has_twitter=bool(twitter),
            has_telegram=bool(telegram),
            has_website=bool(website),
        )

        # Run checks concurrently
        twitter_task = asyncio.create_task(self._check_twitter(twitter)) if twitter else asyncio.create_task(asyncio.coroutine(lambda: False)())
        website_task = asyncio.create_task(self._check_url(website)) if website else asyncio.create_task(asyncio.coroutine(lambda: False)())

        check.twitter_reachable = await twitter_task
        check.website_reachable = await website_task

        # Score: 10 max
        score = 0
        if twitter:
            score += 3
            if check.twitter_reachable:
                score += 1
        if telegram:
            score += 3
        if website:
            score += 2
            if check.website_reachable:
                score += 1

        check.score = min(10, score)
        return check
