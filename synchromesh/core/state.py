import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import yaml

class StateManager:
    """
    Tracks runtime modernization metrics for SynchroMesh.

    Notes:
    - parity_score here is a runtime proxy metric:
      (% LOW-risk exact token matches over total findings)
    - Formal evaluation metrics should be computed separately by the evaluation modules.
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.target_score = float(
            self.config.get("metrics", {}).get("target_parity_score", 95.0)
        )

        self.history: List[Dict[str, Any]] = []
        self._last_metrics: Dict[str, Any] = {}

    def compute_metrics(
        self,
        total_findings: int,
        recommendations: List[Dict[str, Any]],
        patches_applied: int,
        outdated_components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Computes runtime metrics for dashboarding and orchestration.
        """
        risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "UNKNOWN": 0}

        approved_changes_count = 0
        blocked_count = 0
        approval_required_count = 0

        for rec in recommendations:
            level = str(rec.get("risk_level", "UNKNOWN")).upper()
            if level not in risk_counts:
                level = "UNKNOWN"
            risk_counts[level] += 1

            if bool(rec.get("approved", False)):
                approved_changes_count += 1

            gate_reason = str(rec.get("gate_reason", "")).lower()
            if "blocked" in gate_reason:
                blocked_count += 1

            if not bool(rec.get("approved", False)) and level in {"MEDIUM", "HIGH"}:
                approval_required_count += 1

        low_count = risk_counts.get("LOW", 0)

        parity_score = 0.0
        if total_findings > 0:
            parity_score = round((low_count / total_findings) * 100.0, 2)

        fix_success_rate = 0.0
        if low_count > 0:
            fix_success_rate = round((patches_applied / low_count) * 100.0, 2)

        outdated_component_count = len(outdated_components or [])
        outdated_frontend_count = len(
            [
                item for item in (outdated_components or [])
                if str(item.get("type", "")).upper() == "OUTDATED_FRONTEND_COMPONENT"
            ]
        )
        outdated_backend_count = len(
            [
                item for item in (outdated_components or [])
                if str(item.get("type", "")).upper() == "OUTDATED_BACKEND_MODULE"
            ]
        )

        status = "🎯 TARGET MET" if parity_score >= self.target_score else "🚧 IN PROGRESS"

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_findings": total_findings,
            "drift_instances": total_findings,
            "recommendations_total": len(recommendations),
            "risk_counts": risk_counts,
            "approved_changes_count": approved_changes_count,
            "approval_required_count": approval_required_count,
            "blocked_count": blocked_count,
            "patches_applied": patches_applied,
            "fix_success_rate": fix_success_rate,
            "parity_score": parity_score,
            "target_parity_score": self.target_score,
            "outdated_component_count": outdated_component_count,
            "outdated_frontend_count": outdated_frontend_count,
            "outdated_backend_count": outdated_backend_count,
            "status": status,
        }

        self._last_metrics = metrics
        self._record_history("METRICS_COMPUTED", metrics)
        return metrics

    def _record_history(
        self,
        event_type: str,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        self.history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "metrics": metrics or self._last_metrics,
            }
        )

    def export_history(self, path: str = "evaluation/traces/state_history.json") -> str:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

        return path