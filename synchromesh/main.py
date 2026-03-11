import os
import sys
import logging
from pathlib import Path
from typing import Dict
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

def _bool_env_present(value: str | None) -> bool:
    return bool(value and str(value).strip())

def load_environment() -> str:
    """
    Loads environment variables, determines execution mode, and logs startup state.

    Mode priority:
      1. Explicit SYNCHROMESH_MODE=real|mock
      2. Auto-detect real mode if required credentials are present
      3. Otherwise fall back to mock
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
        mode = (
            "real"
            if _bool_env_present(figma_token)
            and _bool_env_present(github_token)
            and _bool_env_present(google_api_key)
            else "mock"
        )

    missing = []
    if not _bool_env_present(figma_token):
        missing.append("FIGMA_ACCESS_TOKEN / FIGMA_API_KEY")
    if not _bool_env_present(github_token):
        missing.append("GITHUB_TOKEN / GITHUB_PERSONAL_ACCESS_TOKEN")
    if not _bool_env_present(google_api_key):
        missing.append("GOOGLE_API_KEY")

    logger.info("====================================")
    logger.info("SynchroMesh Environment Configuration")
    logger.info("Execution Mode: %s", mode.upper())
    logger.info("Figma Token Present: %s", _bool_env_present(figma_token))
    logger.info("GitHub Token Present: %s", _bool_env_present(github_token))
    logger.info("Google API Key Present: %s", _bool_env_present(google_api_key))
    logger.info("Log File: %s", LOG_FILE)
    logger.info("====================================")

    if missing:
        logger.warning("Missing environment configuration: %s", ", ".join(missing))
        logger.warning("System will run in '%s' mode.", mode)
    else:
        logger.info("Environment variables loaded successfully. Mode=%s", mode)

    os.environ["SYNCHROMESH_MODE"] = mode
    return mode

def _startup_summary() -> Dict[str, str]:
    return {
        "mode": os.getenv("SYNCHROMESH_MODE", "mock"),
        "port": os.getenv("SYNCHROMESH_PORT", "8501"),
        "address": os.getenv("SYNCHROMESH_ADDRESS", "0.0.0.0"),
    }

def launch_dashboard() -> None:
    """
    Programmatically launches the Streamlit dashboard.
    """
    dashboard_path = ROOT_DIR / "interaction" / "dashboard" / "app.py"
    if not dashboard_path.exists():
        logger.error("Dashboard file not found at %s", dashboard_path)
        raise FileNotFoundError(f"Dashboard file not found at {dashboard_path}")

    summary = _startup_summary()
    logger.info(
        "Launching SynchroMesh dashboard in %s mode on %s:%s",
        summary["mode"].upper(),
        summary["address"],
        summary["port"],
    )

    sys.argv = [
        "streamlit",
        "run",
        str(dashboard_path),
        f"--server.port={summary['port']}",
        f"--server.address={summary['address']}",
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