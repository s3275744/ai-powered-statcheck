import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

OLMOCR_SERVER = os.getenv("OLMOCR_SERVER")
OLMOCR_API_KEY = os.getenv("OLMOCR_API_KEY")
OLMOCR_MODEL = os.getenv("OLMOCR_MODEL")
