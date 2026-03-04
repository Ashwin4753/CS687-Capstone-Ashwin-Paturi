import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

class ContextStore:
    """
    Shared, auditable memory across orchestrator + agents.

    Stores:
      - detected_drift (ghost style findings)
      - recommendations (stylist output)
      - approved_changes (recommendations marked approved)
      - patches (diffs from Syncer)
      - metrics (parity + run stats)

    Also writes traces for evaluation.
    """

    def __init__(self, trace_dir: str = "evaluation/traces", outputs_dir: str = "outputs"):
        self.trace_dir = trace_dir
        self.outputs_dir = outputs_dir

        self.shared_memory: Dict[str, Any] = {
            "session_start": datetime.now().isoformat(),
            "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "repo": None,
            "figma_file_id": None,
            "detected_drift": [],
            "recommendations": [],
            "approved_changes": [],
            "patches": [],
            "metrics": {},
        }

    def set_run_context(self, repo: str, figma_file_id: str):
        self.shared_memory["repo"] = repo
        self.shared_memory["figma_file_id"] = figma_file_id

    def add_detected_drift(self, findings: List[dict]):
        self.shared_memory["detected_drift"].extend(findings)

    def add_recommendations(self, recs: List[dict]):
        self.shared_memory["recommendations"].extend(recs)

    def set_approved_changes(self, approved: List[dict]):
        self.shared_memory["approved_changes"] = approved

    def add_patches(self, patches: List[dict]):
        self.shared_memory["patches"].extend(patches)

    def set_metrics(self, metrics: Dict[str, Any]):
        self.shared_memory["metrics"] = metrics

    def get_full_context(self) -> Dict[str, Any]:
        return self.shared_memory

    # ---- persistence ----
    def save_session_trace(self) -> str:
        os.makedirs(self.trace_dir, exist_ok=True)
        path = os.path.join(self.trace_dir, f"trace_{self.shared_memory['run_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.shared_memory, f, indent=2)
        return path

    def export_outputs(self) -> Dict[str, str]:
        """
        Writes:
          outputs/drift_report.json
          outputs/recommendations.json
          outputs/approved_changes.json
          outputs/metrics.json
          outputs/patches.json
        """
        os.makedirs(self.outputs_dir, exist_ok=True)

        mapping = {
            "drift_report.json": self.shared_memory["detected_drift"],
            "recommendations.json": self.shared_memory["recommendations"],
            "approved_changes.json": self.shared_memory["approved_changes"],
            "metrics.json": self.shared_memory["metrics"],
            "patches.json": self.shared_memory["patches"],
        }

        out_paths: Dict[str, str] = {}
        for filename, payload in mapping.items():
            p = os.path.join(self.outputs_dir, filename)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            out_paths[filename] = p

        return out_paths