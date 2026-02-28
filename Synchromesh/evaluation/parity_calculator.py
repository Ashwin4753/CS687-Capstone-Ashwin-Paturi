import json
from typing import Dict, List

class ParityCalculator:
    def __init__(self):
        """
        Implements the formula: 
        Parity = (Aligned Components / Total Evaluated Components) * 100
        """
        pass

    def calculate_metrics(self, drift_report: List[Dict], total_components: int) -> Dict:
        # A component is 'aligned' if it has 0 undetected/ghost styles
        drift_by_component = {}
        for item in drift_report:
            comp = item.get('component_name', 'unknown')
            drift_by_component[comp] = drift_by_component.get(comp, 0) + 1
        
        # Count components with no drift
        aligned_count = total_components - len(drift_by_component)
        
        parity_score = (aligned_count / total_components) * 100 if total_components > 0 else 0
        
        return {
            "total_components": total_components,
            "aligned_components": aligned_count,
            "drift_instances": len(drift_report),
            "parity_score": round(parity_score, 2)
        }

    def generate_report(self, session_id: str, metrics: Dict):
        filename = f"evaluation/reports/parity_{session_id}.json"
        with open(filename, 'w') as f:
            json.dump(metrics, f, indent=4)
        print(f"📊 Parity Report generated: {filename}")