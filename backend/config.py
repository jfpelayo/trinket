"""Shared environment loading for the backend.

Load order: repo-root .env first, then backend/.env, both with
override=False so real OS environment variables always win and the
root file wins over the backend-local file.
"""

from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

load_dotenv(ROOT_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=False)
