"""Configuration from the environment (FR-031; research R1, R13)."""

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

SETUP_MESSAGE = (
    "Setup needed: OPENROUTER_API_KEY and MODEL_NAME must be set in .env (see .env.example)."
)
MODEL_TIMEOUT_SECONDS = 30


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    model_name: str


def load_settings(environ: Mapping[str, str]) -> Settings:
    key = environ.get("OPENROUTER_API_KEY", "").strip()
    model_name = environ.get("MODEL_NAME", "").strip()
    if not key or not model_name:
        raise ConfigError(SETUP_MESSAGE)
    return Settings(openrouter_api_key=key, model_name=model_name)


def build_model(settings: Settings) -> OpenRouterModel:
    return OpenRouterModel(
        settings.model_name,
        provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
        settings={"temperature": 0, "timeout": MODEL_TIMEOUT_SECONDS},
    )
