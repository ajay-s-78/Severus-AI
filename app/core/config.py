import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Absolute path to project root .env file
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")

# Load .env file
if os.path.exists(ENV_FILE_PATH):
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)


class Settings(BaseSettings):
    """
    Application Settings configuration.
    Reads environment variables from .env file.
    """

    APP_NAME: str = "SEVERUS - Data Science AI Assistant"

    # Google Gemini API configuration
    GOOGLE_API_KEY: Optional[str] = None

    MODEL_NAME: str = "gemini-3.7-flash"

    DEBUG: bool = True

    PORT: int = 8001

    HOST: str = "0.0.0.0"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def is_placeholder_value(
        self,
        key_val: Optional[str]
    ) -> bool:
        """
        Check if API key is missing or a placeholder.
        """

        if not key_val:
            return True

        cleaned = (
            key_val
            .strip()
            .strip("'")
            .strip('"')
        )

        placeholders = [
            "",
            "your_gemini_api_key",
            "your_gemini_api_key_here",
            "AIza...",
            "your_api_key",
            "your_api_key_here",
            "..."
        ]

        if cleaned.lower() in [
            value.lower() for value in placeholders
        ]:
            return True

        if "your_gemini_api_key" in cleaned.lower():
            return True

        return False

    def get_api_key(self) -> Optional[str]:
        """
        Dynamically retrieve GOOGLE_API_KEY
        from the .env file or environment.
        """

        # Reload .env to ensure latest value is used
        if os.path.exists(ENV_FILE_PATH):
            load_dotenv(
                dotenv_path=ENV_FILE_PATH,
                override=True
            )

        key = (
            os.getenv("GOOGLE_API_KEY")
            or self.GOOGLE_API_KEY
        )

        if key:
            key = (
                key
                .strip()
                .strip("'")
                .strip('"')
            )

        return key


settings = Settings()