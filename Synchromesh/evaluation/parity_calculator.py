import json
import os
from typing import Dict, List, Any


class ParityCalculator:
    """
    Computes design-token parity for runtime evaluation and reporting.

    Current implementation uses file-level alignment as a proxy for component-level parity:
        parity = (aligned_files / total_components) * 100

    Notes:
    - `file_path` is used as the evaluated unit.
    - This is suitable for capstone evaluation, but should be described honestly
      as a file-level/component-proxy metric.
    """

    def calculate_metrics(
        self,
        drift_report: List[Dict[str, Any]],
        total_components: int,
    ) -> Dict[str, Any]:
        """
        Computes parity metrics from a drift report.

        Parameters:
        - drift_report: list of ghost-style findings
        - total_components: total number of evaluated components/files

        Returns:
        - metrics dict suitable for runtime storage, report generation, and JSON export
        """
        drift_by_component: Dict[str, int] = {}
        unknown_path_count = 0

        for item in drift_report:
            component = item.get("file_path")
            if not component:
                unknown_path_count += 1
                continue

            component_key = str(component)
            drift_by_component.setdefault(component_key, 0)
            drift_by_component[component_key] += 1

        components_with_drift = len(drift_by_component)
        aligned_components = max(total_components - components_with_drift, 0)

        parity_score = 0.0
        if total_components > 0:
            parity_score = round((aligned_components / total_components) * 100, 2)

        drift_density = 0.0
        if total_components > 0:
            drift_density = round(len(drift_report) / total_components, 2)

        component_breakdown = [
            {"file_path": file_path, "drift_count": drift_count}
            for file_path, drift_count in sorted(
                drift_by_component.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        metrics = {
            "total_components": total_components,
            "aligned_components": aligned_components,
            "components_with_drift": components_with_drift,
            "drift_instances": len(drift_report),
            "unknown_path_findings": unknown_path_count,
            "parity_score": parity_score,
            "alignment_rate": parity_score,
            "drift_density": drift_density,
            "component_breakdown": component_breakdown,
        }

        return metrics

    def generate_report(self, session_id: str, metrics: Dict[str, Any]) -> str:
        """
        Writes parity metrics to a JSON report file.
        Returns the generated filename.
        """
        os.makedirs("evaluation/reports", exist_ok=True)

        filename = f"evaluation/reports/parity_{session_id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=4)

        return filename