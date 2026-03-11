import json
from datetime import datetime

class ContextStore:
    def __init__(self):
        self.shared_memory = {
            "session_start": datetime.now().isoformat(),
            "detected_drift": [],
            "recommendations": [],
            "approved_changes": []
        }

    def update_shared_memory(self, key: str, value: any):
        if key in self.shared_memory:
            self.shared_memory[key] = value
            print(f"🧠 Shared Context Updated: {key}")

    def get_full_context(self):
        return self.shared_memory

    def save_session_trace(self):
        """Saves reasoning traces for the Evaluation module."""
        with open(f"evaluation/traces/trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(self.shared_memory, f, indent=4)