from google_adk import Agent
from typing import Dict, List

class StylistAgent:
    def __init__(self):
        self.agent = Agent(
            name="Stylist",
            instructions="""
            You are a Design System Expert. Compare the 'Ghost Styles' identified 
            by the Archaeologist against the authoritative Figma Design Tokens. 
            Determine if a match exists. If a match is found, propose a 
            replacement token name. Categorize changes as LOW RISK (token swap) 
            or HIGH RISK (structural change).
            """
        )

    def detect_drift(self, ghost_styles: List[Dict], figma_tokens: Dict) -> List[Dict]:
        """Matches hard-coded values to the closest design token."""
        recommendations = []
        for style in ghost_styles:
            # Simple exact match logic for the prototype
            token_name = figma_tokens.get(style['value'].lower())
            
            recommendations.append({
                "original_value": style['value'],
                "proposed_token": token_name if token_name else "UNKNOWN_TOKEN",
                "line": style['line'],
                "risk_level": "LOW" if token_name else "HIGH",
                "reasoning": f"Matching {style['value']} to design system standards."
            })
        return recommendations