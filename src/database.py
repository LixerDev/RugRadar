import aiosqlite
import json
from datetime import datetime
from src.models import RugReport
from src.logger import get_logger

logger = get_logger(__name__)

DB_PATH = "rugradar.db"


async def init_db():
    """Initialize the RugRadar SQLite database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mint TEXT NOT NULL,
                name TEXT,
                symbol TEXT,
                trust_score INTEGER,
                risk_level TEXT,
                ai_verdict TEXT,
                ai_reasoning TEXT,
                red_flags TEXT,
                positives TEXT,
                mint_auth_score INTEGER,
                holder_score INTEGER,
                creator_score INTEGER,
                bundle_score INTEGER,
                social_score INTEGER,
                liquidity_score INTEGER,
                top10_concentration REAL,
                mint_authority_active INTEGER,
                freeze_authority_active INTEGER,
                bundle_detected INTEGER,
                creator_address TEXT,
                scanned_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    logger.debug("Database initialized.")


async def save_scan(report: RugReport):
    """Persist a scan result to the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO scans (
                    mint, name, symbol, trust_score, risk_level,
                    ai_verdict, ai_reasoning, red_flags, positives,
                    mint_auth_score, holder_score, creator_score,
                    bundle_score, social_score, liquidity_score,
                    top10_concentration, mint_authority_active,
                    freeze_authority_active, bundle_detected, creator_address
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                report.metadata.mint,
                report.metadata.name,
                report.metadata.symbol,
                report.trust_score,
                report.risk_level.value,
                report.ai_verdict,
                report.ai_reasoning,
                json.dumps(report.red_flags),
                json.dumps(report.positives),
                report.mint_check.score,
                report.holder_check.score,
                report.creator_check.score,
                report.bundle_check.score,
                report.social_check.score,
                report.liquidity_check.score,
                report.holder_check.top10_concentration_pct,
                1 if report.mint_check.mint_authority_active else 0,
                1 if report.mint_check.freeze_authority_active else 0,
                1 if report.bundle_check.bundle_detected else 0,
                report.creator_check.creator_address,
            ))
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save scan: {e}")


async def get_scan_history(limit: int = 20) -> list[dict]:
    """Retrieve recent scan history."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM scans ORDER BY scanned_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_stats() -> dict:
    """Get overall scanning statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM scans") as c:
            total = (await c.fetchone())[0]
        async with db.execute("SELECT AVG(trust_score) FROM scans") as c:
            avg_score = (await c.fetchone())[0] or 0
        async with db.execute("SELECT COUNT(*) FROM scans WHERE trust_score < 25") as c:
            likely_rugs = (await c.fetchone())[0]
        return {
            "total_scans": total,
            "avg_trust_score": round(avg_score, 1),
            "likely_rugs_detected": likely_rugs,
        }
