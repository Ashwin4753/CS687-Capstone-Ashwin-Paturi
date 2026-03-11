import json
import os
from datetime import datetime
from typing import Any, Dict, List

class ContextStore:
    """
    Shared, auditable memory across orchestrator + agents.

    Stores:
      - detected_drift
      - outdated_components
      - recommendations
      - approved_changes
      - patches
      - metrics
      - evaluation
      - trace_logs
      - pipeline_status
      - run_timeline
      - report_path

    Also writes traces for evaluation and dashboard use.
    """

    def __init__(self, trace_dir: str = "evaluation/traces", outputs_dir: str = "outputs"):
        self.trace_dir = trace_dir
        self.outputs_dir = outputs_dir
        self.session_start = datetime.now().isoformat()

        self.shared_memory: Dict[str, Any] = {}
        self.start_new_run()

    def start_new_run(self, repo: str | None = None, figma_file_id: str | None = None):
        """
        Resets run-scoped memory for a fresh pipeline execution.
        Keeps session_start stable, refreshes run-specific metadata.
        """
        self.shared_memory = {
            "session_start": self.session_start,
            "run_start": datetime.now().isoformat(),
            "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "repo": repo,
            "figma_file_id": figma_file_id,
            "detected_drift": [],
            "outdated_components": [],
            "recommendations": [],
            "approved_changes": [],
            "patches": [],
            "metrics": {},
            "evaluation": {},
            "trace_logs": [],
            "pipeline_status": [],
            "run_timeline": [],
            "report_path": None,
        }

    def set_run_context(self, repo: str, figma_file_id: str):
        self.start_new_run(repo=repo, figma_file_id=figma_file_id)

    def add_detected_drift(self, findings: List[dict]):
        self.shared_memory["detected_drift"].extend(findings)

    def add_outdated_components(self, findings: List[dict]):
        self.shared_memory["outdated_components"].extend(findings)

    def add_recommendations(self, recs: List[dict]):
        self.shared_memory["recommendations"].extend(recs)

    def set_approved_changes(self, approved: List[dict]):
        self.shared_memory["approved_changes"] = approved

    def add_patches(self, patches: List[dict]):
        self.shared_memory["patches"].extend(patches)

    def set_metrics(self, metrics: Dict[str, Any]):
        self.shared_memory["metrics"] = metrics

    def set_evaluation(self, evaluation: Dict[str, Any]):
        self.shared_memory["evaluation"] = evaluation

    def add_trace_logs(self, logs: List[dict]):
        self.shared_memory["trace_logs"].extend(logs)

    def set_pipeline_status(self, stages: List[dict]):
        self.shared_memory["pipeline_status"] = stages

    def set_run_timeline(self, timeline: List[dict]):
        self.shared_memory["run_timeline"] = timeline

    def set_report_path(self, report_path: str):
        self.shared_memory["report_path"] = report_path

    def get_full_context(self) -> Dict[str, Any]:
        return self.shared_memory

    def save_session_trace(self) -> str:
        os.makedirs(self.trace_dir, exist_ok=True)
        path = os.path.join(self.trace_dir, f"trace_{self.shared_memory['run_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.shared_memory, f, indent=2)
        return path

    def export_outputs(self) -> Dict[str, str]:
        """
        Writes current-run outputs:
          outputs/drift_report.json
          outputs/outdated_components.json
          outputs/recommendations.json
          outputs/approved_changes.json
          outputs/metrics.json
          outputs/patches.json
          outputs/evaluation.json
          outputs/trace_logs.json
          outputs/pipeline_status.json
          outputs/run_timeline.json
        """
        os.makedirs(self.outputs_dir, exist_ok=True)

        mapping = {
            "drift_report.json": self.shared_memory["detected_drift"],
            "outdated_components.json": self.shared_memory["outdated_components"],
            "recommendations.json": self.shared_memory["recommendations"],
            "approved_changes.json": self.shared_memory["approved_changes"],
            "metrics.json": self.shared_memory["metrics"],
            "patches.json": self.shared_memory["patches"],
            "evaluation.json": self.shared_memory["evaluation"],
            "trace_logs.json": self.shared_memory["trace_logs"],
            "pipeline_status.json": self.shared_memory["pipeline_status"],
            "run_timeline.json": self.shared_memory["run_timeline"],
        }

        out_paths: Dict[str, str] = {}
        for filename, payload in mapping.items():
            path = os.path.join(self.outputs_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            out_paths[filename] = path

        if self.shared_memory.get("report_path"):
            out_paths["report_path"] = self.shared_memory["report_path"]

        return out_paths