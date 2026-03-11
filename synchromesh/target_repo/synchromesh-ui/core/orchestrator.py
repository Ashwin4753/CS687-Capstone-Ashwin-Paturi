from typing import Dict
from agents.archaeologist import ArchaeologistAgent
from agents.stylist import StylistAgent
from agents.syncer import SyncerAgent
from core.context_store import ContextStore

class SynchroMeshOrchestrator:
    def __init__(self):
        self.archaeologist = ArchaeologistAgent()
        self.stylist = StylistAgent()
        self.syncer = SyncerAgent()
        self.context = ContextStore()

    async def run_sync_pipeline(self, repo_url: str, figma_file_id: str):
        print(f"🚀 Starting Sync Pipeline for: {repo_url}")
        
        # 1. Digital Archaeology Phase
        # In a real app, you'd fetch file content via GitHub MCP here
        sample_code = "const primaryBtn = { color: '#3b82f6', margin: '10px' };"
        ghost_styles = self.archaeologist.find_ghost_styles(sample_code)
        self.context.update_shared_memory("detected_drift", ghost_styles)

        # 2. Design Alignment Phase
        # Fetching Figma tokens via Figma MCP
        mock_figma_tokens = {"#3b82f6": "var(--blue-500)"} 
        recommendations = self.stylist.detect_drift(ghost_styles, mock_figma_tokens)
        self.context.update_shared_memory("recommendations", recommendations)

        # 3. Risk Assessment & Governance
        high_risk_items = [r for r in recommendations if r['risk_level'] == "HIGH"]
        
        if high_risk_items:
            print("⚠️ High Risk detected. Awaiting Human-in-the-loop approval...")
            return "AWAITING_APPROVAL"

        # 4. Execution Phase
        sync_result = await self.syncer.apply_token_swap(repo_url, recommendations, None)
        return sync_result