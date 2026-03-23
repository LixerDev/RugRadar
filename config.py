import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GPT_MODEL: str = os.getenv("GPT_MODEL", "gpt-4o-mini")
    GPT_MAX_TOKENS: int = int(os.getenv("GPT_MAX_TOKENS", "600"))

    # Solana
    SOLANA_RPC_URL: str = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    HELIUS_API_KEY: str = os.getenv("HELIUS_API_KEY", "")
    BIRDEYE_API_KEY: str = os.getenv("BIRDEYE_API_KEY", "")

    # Analysis
    MAX_HOLDERS_TO_FETCH: int = int(os.getenv("MAX_HOLDERS_TO_FETCH", "20"))
    HOLDER_CONCENTRATION_THRESHOLD: int = int(os.getenv("HOLDER_CONCENTRATION_THRESHOLD", "60"))
    NEW_TOKEN_AGE_THRESHOLD: int = int(os.getenv("NEW_TOKEN_AGE_THRESHOLD", "3600"))

    # Watch mode
    PUMP_WS_URL: str = os.getenv("PUMP_WS_URL", "wss://pumpportal.fun/api/data")
    ALERT_THRESHOLD: int = int(os.getenv("ALERT_THRESHOLD", "40"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "true").lower() == "true"

    def validate(self) -> list[str]:
        errors = []
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
        if not self.SOLANA_RPC_URL:
            errors.append("SOLANA_RPC_URL is required")
        return errors

config = Config()
