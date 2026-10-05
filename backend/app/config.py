import os
from dotenv import load_dotenv

# Load backend/.env before reading configuration values.
_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=_ENV_PATH, override=False)

WORKSPACES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "workspaces")
)

class Config:
    WORKSPACES_DIR = WORKSPACES_DIR
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    MAX_TOOL_CALLS = int(os.environ.get("MAX_TOOL_CALLS", "12"))
