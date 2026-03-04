import json
import os
from typing import Dict, List

class ParityCalculator:
    """
    Computes Design Token Parity.

    Parity = (Aligned Components / Total Components) * 100
    """

    def calculate_metrics(self, drift_report: List[Dict], total_components: int) -> Dict:

        # Group drift by component/file
        drift_by_component = {}

        for item in drift_report:
            comp = item.get("file_path", "unknown_component")
            drift_by_component.setdefault(comp, 0)
            drift_by_component[comp] += 1

        aligned_components = total_components - len(drift_by_component)

        parity_score = (
            (aligned_components / total_components) * 100
            if total_components > 0
            else 0
        )

        metrics = {
            "total_components": total_components,
            "aligned_components": aligned_components,
            "components_with_drift": len(drift_by_component),
            "drift_instances": len(drift_report),
            "parity_score": round(parity_score, 2),
        }

        return metrics

    def generate_report(self, session_id: str, metrics: Dict):

        os.makedirs("evaluation/reports", exist_ok=True)

        filename = f"evaluation/reports/parity_{session_id}.json"

        with open(filename, "w") as f:
            json.dump(metrics, f, indent=4)

        print(f"📊 Parity Report generated: {filename}")