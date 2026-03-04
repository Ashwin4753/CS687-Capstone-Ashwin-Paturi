import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import yaml

class StateManager:
    """
    Tracks evaluation metrics & parity score.
    Uses config/settings.yaml to get target parity score.
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.target_score = float(self.config.get("metrics", {}).get("target_parity_score", 95.0))

        self.history: List[Dict[str, Any]] = []
        self._last_metrics: Dict[str, Any] = {}

    def compute_metrics(
        self,
        total_findings: int,
        recommendations: List[Dict[str, Any]],
        patches_applied: int,
    ) -> Dict[str, Any]:
        """
        A capstone-credible metric set:
          - parity_score: proxy = % findings with LOW (exact token match)
          - counts by risk
          - applied fixes
        """
        risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "UNKNOWN": 0}
        for r in recommendations:
            lvl = str(r.get("risk_level", "UNKNOWN")).upper()
            risk_counts[lvl] = risk_counts.get(lvl, 0) + 1

        # Proxy parity: low-risk matched tokens / total findings
        parity_score = 0.0
        if total_findings > 0:
            parity_score = round((risk_counts.get("LOW", 0) / total_findings) * 100.0, 2)

        status = "🎯 TARGET MET" if parity_score >= self.target_score else "🚧 IN PROGRESS"

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_findings": total_findings,
            "recommendations_total": len(recommendations),
            "risk_counts": risk_counts,
            "patches_applied": patches_applied,
            "parity_score": parity_score,
            "target_parity_score": self.target_score,
            "status": status,
        }

        self._last_metrics = metrics
        self._record_history("METRICS_COMPUTED", metrics)
        return metrics

    def _record_history(self, event_type: str, metrics: Optional[Dict[str, Any]] = None):
        self.history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "metrics": metrics or self._last_metrics,
            }
        )

    def export_history(self, path: str = "evaluation/traces/state_history.json") -> str:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)
        return path