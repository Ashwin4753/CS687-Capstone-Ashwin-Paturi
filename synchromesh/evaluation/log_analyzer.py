import csv
import os
from datetime import datetime
from typing import Any, Dict, List


class LogAnalyzer:
    """
    Analyzes structured agent reasoning traces for runtime explainability
    and evaluation reporting.

    Expected trace shape (best effort):
    {
        "agent_name": "Stylist",
        "action_taken": "generated LOW recommendation",
        "confidence_score": 0.91,
        "timestamp": "2026-03-05T12:34:56",
        "file_path": "src/components/Button.tsx",
        "line": 14,
        "token": "color.primary.500"
    }

    Notes:
    - If confidence_score is missing or invalid, it is excluded from averaging.
    - This module is used by the orchestrator for live evaluation metrics and report generation.
    """

    def extract_reasoning_stats(self, trace_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes:
        - total trace coverage
        - average confidence by agent
        - action counts by agent
        """
        agent_confidence: Dict[str, List[float]] = {}
        action_counts_by_agent: Dict[str, int] = {}
        missing_confidence = 0

        for entry in trace_logs:
            agent = str(entry.get("agent_name", "unknown"))
            confidence = entry.get("confidence_score")

            action_counts_by_agent[agent] = action_counts_by_agent.get(agent, 0) + 1

            if isinstance(confidence, (int, float)):
                agent_confidence.setdefault(agent, []).append(float(confidence))
            else:
                missing_confidence += 1

        average_confidence_by_agent: Dict[str, float] = {}
        for agent, scores in agent_confidence.items():
            if scores:
                average_confidence_by_agent[agent] = round(sum(scores) / len(scores), 3)

        return {
            "entries_total": len(trace_logs),
            "entries_with_confidence": sum(len(v) for v in agent_confidence.values()),
            "entries_missing_confidence": missing_confidence,
            "average_confidence_by_agent": average_confidence_by_agent,
            "action_counts_by_agent": action_counts_by_agent,
        }

    def export_for_thesis(self, trace_logs: List[Dict[str, Any]]) -> str:
        """
        Exports trace logs to CSV for charts, reports, and audit review.
        Returns the generated filename.
        """
        os.makedirs("evaluation/data_exports", exist_ok=True)

        filename = f"evaluation/data_exports/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        fieldnames = [
            "agent_name",
            "action_taken",
            "confidence_score",
            "timestamp",
            "file_path",
            "line",
            "token",
        ]

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for entry in trace_logs:
                row = {
                    "agent_name": entry.get("agent_name", "unknown"),
                    "action_taken": entry.get("action_taken", ""),
                    "confidence_score": entry.get("confidence_score", ""),
                    "timestamp": entry.get("timestamp", ""),
                    "file_path": entry.get("file_path", ""),
                    "line": entry.get("line", ""),
                    "token": entry.get("token", ""),
                }
                writer.writerow(row)

        return filename