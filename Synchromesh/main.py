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

LOG_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Logging
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
    Loads environment variables and determines execution mode.

    Returns:
        "real" or "mock"
    """
    load_dotenv()

    figma_token = os.getenv("FIGMA_ACCESS_TOKEN") or os.getenv("FIGMA_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    forced_mode = (os.getenv("SYNCHROMESH_MODE") or "").strip().lower()
    if forced_mode in {"mock", "real"}:
        mode = forced_mode
        logger.info("SYNCHROMESH_MODE override detected: %s", mode)
    else:
        mode = "real" if figma_token and github_token and google_api_key else "mock"

    missing = []
    if not figma_token:
        missing.append("FIGMA_ACCESS_TOKEN / FIGMA_API_KEY")
    if not github_token:
        missing.append("GITHUB_TOKEN / GITHUB_PERSONAL_ACCESS_TOKEN")
    if not google_api_key:
        missing.append("GOOGLE_API_KEY")

    if missing:
        logger.warning("Missing environment configuration: %s", ", ".join(missing))
        logger.warning("System will run in '%s' mode.", mode)
    else:
        logger.info("Environment variables loaded successfully. Mode=%s", mode)

    os.environ["SYNCHROMESH_MODE"] = mode
    return mode

def launch_dashboard() -> None:
    """
    Programmatically launches the Streamlit dashboard.
    """
    logger.info("Initializing SynchroMesh Dashboard...")

    dashboard_path = ROOT_DIR / "interaction" / "dashboard" / "app.py"

    if not dashboard_path.exists():
        logger.error("Dashboard file not found at %s", dashboard_path)
        raise FileNotFoundError(f"Dashboard file not found at {dashboard_path}")

    port = os.getenv("SYNCHROMESH_PORT", "8501")
    address = os.getenv("SYNCHROMESH_ADDRESS", "0.0.0.0")
    mode = os.getenv("SYNCHROMESH_MODE", "mock")

    logger.info("Launching dashboard in %s mode on %s:%s", mode.upper(), address, port)

    sys.argv = [
        "streamlit",
        "run",
        str(dashboard_path),
        f"--server.port={port}",
        f"--server.address={address}",
    ]

    try:
        stcli.main()
    except Exception as exc:
        logger.exception("Failed to launch Streamlit dashboard: %s", exc)
        raise

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