"""Central configuration.

Every path and setting lives here so the servers, the client and the UI
agree on where data is stored. Values can be overridden with environment
variables (loaded from a .env file in the project root).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "productivity.db"))
NOTES_DIR = Path(os.getenv("NOTES_DIR", DATA_DIR / "notes"))
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", DATA_DIR / "documents"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if ANTHROPIC_API_KEY.endswith("..."):  # untouched placeholder from .env.example
    ANTHROPIC_API_KEY = ""
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "8"))

USER_NAME = os.getenv("USER_NAME", "Hamza")
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Nova")

for _d in (DATA_DIR, NOTES_DIR, DOCUMENTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
