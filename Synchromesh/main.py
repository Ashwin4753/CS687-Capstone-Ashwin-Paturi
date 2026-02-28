import os
import sys
import logging
from dotenv import load_dotenv
import streamlit.web.cli as stcli

# 1. Setup Logging for Auditability (Instructor's Requirement)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("evaluation/system_logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SynchroMesh-Root")

def load_environment():
    """Loads API keys for Figma, GitHub, and LLM providers."""
    load_dotenv()
    required_keys = ["FIGMA_ACCESS_TOKEN", "GITHUB_TOKEN", "GOOGLE_API_KEY"]
    
    missing = [key for key in required_keys if not os.getenv(key)]
    if missing:
        logger.warning(f"Missing API keys in .env: {', '.join(missing)}")
        logger.warning("System will run in 'Mock/Offline Mode'.")
    else:
        logger.info("Environment variables loaded successfully.")

def launch_dashboard():
    """
    Programmatically launches the Streamlit dashboard 
    located in the interaction layer.
    """
    logger.info("Initializing SynchroMesh Dashboard...")
    
    # Path to the actual Streamlit app file
    dashboard_path = os.path.join(
        os.path.dirname(__file__), 
        "interaction", 
        "dashboard", 
        "app.py"
    )
    
    # Check if the file exists before launching
    if not os.path.exists(dashboard_path):
        logger.error(f"Dashboard file not found at {dashboard_path}")
        sys.exit(1)

    # Injecting 'streamlit run' command into system arguments
    sys.argv = [
        "streamlit",
        "run",
        dashboard_path,
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    print("""
    ==================================================
    SYNCHROMESH: AGENTIC DESIGN-CODE ORCHESTRATOR
    ==================================================
    """)
    load_environment()
    launch_dashboard()