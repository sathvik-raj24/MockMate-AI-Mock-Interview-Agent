"""Settings come from .env / environment. Nothing provider-specific is hard-coded here
except a convenient default model for the NVIDIA provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODELS = {"nvidia": "meta/llama-3.3-70b-instruct"}


class ConfigError(Exception):
    """Raised for missing or invalid configuration (shown to the user, no traceback)."""


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    api_key: str
    workspace: Path
    questions: int
    db_path: Path


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build Settings. Pass `env` in tests; otherwise .env is loaded into os.environ."""
    if env is None:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
        env = os.environ

    provider = env.get("MODEL_PROVIDER", "nvidia").strip().lower()
    model = env.get("MODEL_NAME", "").strip() or DEFAULT_MODELS.get(provider, "")
    if provider == "fake":
        model = model or "fake"
    if not model:
        raise ConfigError(f"MODEL_NAME is required for provider '{provider}'. Set it in .env.")

    key_var = f"{provider.upper()}_API_KEY"
    api_key = (env.get(key_var) or env.get("MODEL_API_KEY") or "").strip()
    if provider != "fake":
        if not api_key:
            raise ConfigError(f"Missing {key_var}. Copy .env.example to .env and add your key.")
        if "your-key" in api_key.lower():
            raise ConfigError(f"{key_var} still has the placeholder value from .env.example.")

    try:
        questions = int(env.get("QUESTIONS_PER_SESSION", "5"))
    except ValueError as exc:
        raise ConfigError("QUESTIONS_PER_SESSION must be a whole number.") from exc
    questions = max(1, min(questions, 20))

    workspace = Path(env.get("MOCKMATE_WORKSPACE") or PROJECT_ROOT / "workspace")
    return Settings(
        provider=provider,
        model=model,
        api_key=api_key,
        workspace=workspace,
        questions=questions,
        db_path=workspace / ".checkpoints.sqlite",
    )
