"""Shared settings and paths. Every script imports from here."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root = one level above src/, so scripts work no matter where you run them from
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# API key is read from the .env file in the repo root (never committed to git)
load_dotenv(ROOT / ".env")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

START_YEAR = 2010
END_YEAR = 2025

RAW_MOVIES_CSV = DATA_DIR / "movies_raw.csv"
