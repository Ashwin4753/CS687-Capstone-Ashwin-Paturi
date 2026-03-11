import pandas as pd
from datetime import datetime

class LogAnalyzer:
    """
    Analyzes agentic reasoning traces to validate the 'Explainability' 
    pillar of the SynchroMesh framework.
    """
    
    def extract_reasoning_stats(self, trace_logs: List[Dict]):
        # Convert agent memory into a structured DataFrame for the paper's charts
        data = []
        for entry in trace_logs:
            data.append({
                "agent": entry.get("agent_name"),
                "action": entry.get("action_taken"),
                "confidence": entry.get("confidence_score", 0.9), # Mock confidence
                "timestamp": entry.get("timestamp")
            })
        
        df = pd.DataFrame(data)
        
        # Calculate Average Confidence per Agent for your thesis table
        summary = df.groupby('agent')['confidence'].mean().to_dict()
        return summary

    def export_for_thesis(self, df: pd.DataFrame):
        # Exports to CSV so you can easily import it into Excel/Google Sheets for your paper
        df.to_csv(f"evaluation/data_exports/run_{datetime.now().strftime('%Y%m%d')}.csv")