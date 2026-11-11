"""Reads optional secrets (API keys) from the environment or from backend/.env."""
import os

from dotenv import dotenv_values


def get_secret(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        value = dotenv_values(".env").get(name)
    return value or None
