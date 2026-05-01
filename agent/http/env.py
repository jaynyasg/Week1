"""Load local `.env` into process env (optional dependency)."""

from __future__ import annotations


def load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dev extra
        return
    load_dotenv()
