import csv
import os
from datetime import datetime
from typing import Dict, List

class LogAnalyzer:
    """
    Analyzes agent reasoning traces to validate explainability.
    """

    def extract_reasoning_stats(self, trace_logs: List[Dict]) -> Dict:
        agent_confidence = {}
        
        for entry in trace_logs:
            agent = entry.get("agent_name", "unknown")
            confidence = entry.get("confidence_score", 0.9)
            agent_confidence.setdefault(agent, [])
            agent_confidence[agent].append(confidence)
        summary = {}

        for agent, scores in agent_confidence.items():
            avg_conf = sum(scores) / len(scores)
            summary[agent] = round(avg_conf, 3)
        return summary

    def export_for_thesis(self, trace_logs: List[Dict]):
        os.makedirs("evaluation/data_exports", exist_ok=True)
        filename = f"evaluation/data_exports/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        keys = ["agent_name", "action_taken", "confidence_score", "timestamp"]

        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()

            for entry in trace_logs:
                writer.writerow(entry)
        print(f"📄 Exported explainability dataset: {filename}")