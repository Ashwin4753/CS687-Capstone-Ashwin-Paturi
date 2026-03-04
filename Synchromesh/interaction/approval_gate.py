import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("SynchroMesh-ApprovalGate")

def _make_change_id(rec: Dict[str, Any]) -> str:
    """
    Deterministic ID for audit + UI selection.
    Uses stable fields present in recommendations.
    """
    key = (
        f"{rec.get('file_path','')}|{rec.get('line','')}|"
        f"{rec.get('original_value','')}|{rec.get('replacement_text','')}"
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

class ApprovalGate:
    """
    Governance gate for staged autonomy (bounded autonomy model).

    IMPORTANT: This gate does NOT decide token correctness.
    Risk levels are produced by StylistAgent:
      - LOW: exact match token swap (safe)
      - MEDIUM: approximate match (approval required)
      - HIGH: unknown/inline/structural (approval required or blocked)

    This gate enforces governance policies and returns UI-friendly buckets.
    """

    def __init__(
        self,
        auto_approve_low_risk: bool = False,
        require_approval_for: Optional[Set[str]] = None,
        max_files_per_sync: int = 10,
        restricted_directories: Optional[List[str]] = None,
    ):
        self.auto_approve_low_risk = auto_approve_low_risk
        self.require_approval_for = {x.upper() for x in (require_approval_for or {"MEDIUM", "HIGH"})}
        self.max_files_per_sync = int(max_files_per_sync)
        self.restricted_directories = restricted_directories or []

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Sorts recommendations into buckets for the dashboard.

        Returns:
          - autonomous: LOW-risk items that can proceed (auto-approved if enabled)
          - approval_required: MEDIUM/HIGH or governance-flagged items
          - blocked: restricted directory items (never auto-apply)
        """
        categorized = {
            "autonomous": [],
            "approval_required": [],
            "blocked": [],
        }

        touched_files = {r.get("file_path") for r in recommendations if r.get("file_path")}
        too_many_files = len(touched_files) > self.max_files_per_sync

        for rec in recommendations:
            r = dict(rec)  # don't mutate input objects
            r["change_id"] = r.get("change_id") or _make_change_id(r)

            file_path = str(r.get("file_path", ""))

            # Block restricted directories outright
            if self._is_restricted(file_path):
                r["approved"] = False
                r["gate_reason"] = "Blocked: restricted directory (governance policy)."
                categorized["blocked"].append(r)
                continue

            risk = str(r.get("risk_level", "HIGH")).upper()

            # If run touches too many files, require approval even for LOW
            if too_many_files:
                r["approved"] = False
                r["gate_reason"] = (
                    f"Approval required: run touches {len(touched_files)} files "
                    f"(max_files_per_sync={self.max_files_per_sync})."
                )
                categorized["approval_required"].append(r)
                continue

            # Approval-required by risk policy
            if risk in self.require_approval_for:
                r["approved"] = False
                r["gate_reason"] = f"Approval required by policy for risk_level={risk}."
                categorized["approval_required"].append(r)
                continue

            # LOW risk path
            if risk == "LOW":
                r["approved"] = bool(self.auto_approve_low_risk)
                r["gate_reason"] = "Auto-approved low-risk change." if r["approved"] else "Low-risk: awaiting approval."
                (categorized["autonomous"] if r["approved"] else categorized["approval_required"]).append(r)
                continue

            # Unknown risk -> safe default
            r["approved"] = False
            r["gate_reason"] = f"Unrecognized risk_level='{risk}', defaulting to approval required."
            categorized["approval_required"].append(r)

        logger.info(
            "ApprovalGate results: autonomous=%d, approval_required=%d, blocked=%d",
            len(categorized["autonomous"]),
            len(categorized["approval_required"]),
            len(categorized["blocked"]),
        )
        return categorized

    def apply_human_approvals(
        self,
        recommendations: List[Dict[str, Any]],
        approved_change_ids: Set[str],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Marks recommendations as approved=True based on selected change_ids from UI.
        Adds audit fields for traceability.
        """
        updated: List[Dict[str, Any]] = []
        for rec in recommendations:
            r = dict(rec)
            r["change_id"] = r.get("change_id") or _make_change_id(r)

            if r["change_id"] in approved_change_ids:
                r["approved"] = True
                r["approved_by"] = user_id
                r["approved_at"] = datetime.now().isoformat()
                self.validate_human_signature(user_id=user_id, change_id=r["change_id"])
            else:
                r["approved"] = bool(r.get("approved", False))

            updated.append(r)

        return updated

    def validate_human_signature(self, user_id: str, change_id: str) -> bool:
        """
        Ensures an audit trail is created for the Explainability requirement.
        In production, this would write to an audit log / DB.
        """
        logger.info("AUDIT: user=%s approved change_id=%s", user_id, change_id)
        return True

    def _is_restricted(self, path: str) -> bool:
        if not path:
            return False
        p = path.replace("\\", "/")
        for rd in self.restricted_directories:
            r = str(rd).replace("\\", "/").rstrip("/")
            if not r:
                continue
            if p.startswith(r) or p.startswith(r.lstrip("/")):
                return True
        return False