import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Primary LLM Configuration (Generic and works with any API provider)
API_KEY = os.getenv("API_KEY", "").strip()
BASE_URL = os.getenv("BASE_URL", "").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "auto").strip()

# Local Free Fallback Configuration (Defaults to local Ollama)
FALLBACK_BASE_URL = os.getenv("FALLBACK_BASE_URL", "http://localhost:11434/v1").strip()
FALLBACK_MODEL_NAME = os.getenv("FALLBACK_MODEL_NAME", "auto").strip()

# Storage Configuration
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma"))
Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(DATA_DIR / "react_research.db"))
SQLALCHEMY_DATABASE_URI = f"sqlite:///{SQLITE_DB_PATH}"

PDF_STORAGE_DIR = os.getenv("PDF_STORAGE_DIR", str(DATA_DIR / "pdfs"))
Path(PDF_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

# ReAct Agent Limits
MAX_STEPS = 10
RATE_LIMIT_DELAY = 3.0  # seconds between arXiv API calls

# Flask Server Configuration
PORT = int(os.getenv("PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_ENV", "development") == "development"
