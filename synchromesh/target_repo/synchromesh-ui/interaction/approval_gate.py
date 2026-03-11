import logging
from typing import Dict, List

logger = logging.getLogger("SynchroMesh-ApprovalGate")

class ApprovalGate:
    def __init__(self, high_risk_threshold: int = 5):
        """
        Initializes the gatekeeper for agentic actions.
        :param high_risk_threshold: Number of files/lines changed before 
                                    forcing a manual review.
        """
        self.high_risk_threshold = high_risk_threshold

    def classify_risk(self, recommendation: Dict) -> str:
        """
        Logic to determine if a change is 'Low Risk' or 'High Risk'.
        This implements the 'Governance' pillar of the SynchroMesh framework.
        """
        # Criteria 1: Type of change
        # Token swaps (colors, spacing) are generally low risk.
        # Layout changes (Flex, Grid, Width) are high risk.
        is_structural = any(kw in recommendation.get('proposed_token', '').lower() 
                            for kw in ['layout', 'grid', 'flex', 'padding'])

        # Criteria 2: Confidence Score from the Agent (ADK metadata)
        confidence = recommendation.get('confidence', 1.0)

        if is_structural or confidence < 0.85:
            return "HIGH"
        return "LOW"

    def process_recommendations(self, recommendations: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Sorts recommendations into buckets for the Streamlit dashboard.
        """
        categorized = {
            "autonomous": [],  # Low risk: can be auto-executed
            "review_required": [] # High risk: requires human eyes
        }

        for rec in recommendations:
            risk = self.classify_risk(rec)
            rec['risk_level'] = risk
            
            if risk == "LOW":
                categorized["autonomous"].append(rec)
            else:
                categorized["review_required"].append(rec)

        logger.info(f"Gatekeeper: {len(categorized['review_required'])} items flagged for manual review.")
        return categorized

    def validate_human_signature(self, user_id: str, change_id: str) -> bool:
        """
        Ensures an audit trail is created for the 'Explainability' requirement.
        """
        # In a production capstone, this would write to an audit log or database
        logger.info(f"User {user_id} manually approved change {change_id}")
        return True