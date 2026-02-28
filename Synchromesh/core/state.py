import yaml
import json
from datetime import datetime

class StateManager:
    def __init__(self, config_path: str = "config/settings.yaml"):
        # Load targets from the YAML configuration
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.total_components = 0
        self.aligned_components = 0
        self.history = []
        
        # Pull threshold from YAML: metrics -> target_parity_score
        self.target_score = self.config.get('metrics', {}).get('target_parity_score', 95.0)

    def set_baseline(self, total: int, aligned: int):
        self.total_components = total
        self.aligned_components = aligned
        self._record_history("BASELINE")

    def calculate_parity_score(self) -> float:
        if self.total_components == 0:
            return 0.0
        return round((self.aligned_components / self.total_components) * 100, 2)

    def get_status(self) -> str:
        """Compares current state against settings.yaml targets."""
        current = self.calculate_parity_score()
        if current >= self.target_score:
            return "🎯 TARGET MET"
        return "🚧 IN PROGRESS"

    def update_after_sync(self, fixed_count: int, agent_name: str = "Syncer"):
        self.aligned_components += fixed_count
        new_score = self.calculate_parity_score()
        self._record_history(f"SYNC_BY_{agent_name.upper()}")
        print(f"📈 {self.get_status()} | New Parity: {new_score}% (Target: {self.target_score}%)")

    def _record_history(self, event_type: str):
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "score": self.calculate_parity_score(),
            "target": self.target_score,
            "status": self.get_status()
        })