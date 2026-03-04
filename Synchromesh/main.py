import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import streamlit.web.cli as stcli

# -----------------------------
# Paths / directories
# -----------------------------
ROOT_DIR = Path(__file__).resolve().parent
EVAL_DIR = ROOT_DIR / "evaluation"
LOG_DIR = EVAL_DIR
LOG_FILE = LOG_DIR / "system_logs.log"

# Ensure directories exist BEFORE logging handlers are attached
LOG_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# 1. Setup Logging for Auditability
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("SynchroMesh-Root")

def load_environment() -> str:
    """
    Loads API keys for Figma, GitHub, and LLM providers.
    Returns an execution mode string: "real" or "mock".
    """
    load_dotenv()

    required_keys = ["FIGMA_ACCESS_TOKEN", "GITHUB_TOKEN", "GOOGLE_API_KEY"]
    missing = [key for key in required_keys if not os.getenv(key)]

    # Explicit user override: SYNCHROMESH_MODE=mock|real
    forced_mode = (os.getenv("SYNCHROMESH_MODE") or "").strip().lower()
    if forced_mode in {"mock", "real"}:
        mode = forced_mode
        logger.info("SYNCHROMESH_MODE override detected: %s", mode)
    else:
        mode = "mock" if missing else "real"

    if missing:
        logger.warning("Missing API keys in .env: %s", ", ".join(missing))
        logger.warning("System will run in '%s' mode.", mode)
    else:
        logger.info("Environment variables loaded successfully. Mode=%s", mode)

    # Make mode accessible to Streamlit/app code
    os.environ["SYNCHROMESH_MODE"] = mode
    return mode

def launch_dashboard():
    """
    Programmatically launches the Streamlit dashboard located in the interaction layer.
    """
    logger.info("Initializing SynchroMesh Dashboard...")

    dashboard_path = ROOT_DIR / "interaction" / "dashboard" / "app.py"

    if not dashboard_path.exists():
        logger.error("Dashboard file not found at %s", dashboard_path)
        raise FileNotFoundError(f"Dashboard file not found at {dashboard_path}")

    # Optional: allow overriding port/address via env for flexibility
    port = os.getenv("SYNCHROMESH_PORT", "8501")
    address = os.getenv("SYNCHROMESH_ADDRESS", "0.0.0.0")

    sys.argv = [
        "streamlit",
        "run",
        str(dashboard_path),
        f"--server.port={port}",
        f"--server.address={address}",
    ]

    # Run Streamlit
    stcli.main()

if __name__ == "__main__":
    print(
        """
==================================================
SYNCHROMESH: AGENTIC DESIGN-CODE ORCHESTRATOR
==================================================
"""
    )
    load_environment()
    launch_dashboard()