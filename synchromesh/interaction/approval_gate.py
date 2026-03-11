import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("SynchroMesh-ApprovalGate")


def _make_change_id(rec: Dict[str, Any]) -> str:
    """
    Deterministic ID for audit + UI selection.
    Uses stable recommendation fields.
    """
    key = (
        f"{rec.get('file_path', '')}|"
        f"{rec.get('line', '')}|"
        f"{rec.get('original_value', '')}|"
        f"{rec.get('replacement_text', '')}"
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


class ApprovalGate:
    """
    Governance gate for staged autonomy.

    IMPORTANT:
    - This gate does NOT decide token correctness.
    - Risk levels are expected to be assigned by StylistAgent:
        LOW    = exact token swap
        MEDIUM = approximate match requiring approval
        HIGH   = unknown / inline / structural / unsupported

    Responsibilities:
    - enforce governance policy
    - assign recommendations to UI-friendly buckets
    - attach stable change IDs
    - support audit fields for human approvals
    """

    def __init__(
        self,
        auto_approve_low_risk: bool = False,
        require_approval_for: Optional[Set[str]] = None,
        max_files_per_sync: int = 10,
        restricted_directories: Optional[List[str]] = None,
    ):
        self.auto_approve_low_risk = bool(auto_approve_low_risk)
        self.require_approval_for = {
            item.upper() for item in (require_approval_for or {"MEDIUM", "HIGH"})
        }
        self.max_files_per_sync = int(max_files_per_sync)
        self.restricted_directories = restricted_directories or []

    def process_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Buckets recommendations for governance/UI.

        Returns:
          - autonomous
          - approval_required
          - blocked
        """
        categorized = {
            "autonomous": [],
            "approval_required": [],
            "blocked": [],
        }

        touched_files = {
            rec.get("file_path")
            for rec in recommendations
            if rec.get("file_path")
        }
        too_many_files = len(touched_files) > self.max_files_per_sync

        for rec in recommendations:
            item = dict(rec)
            item["change_id"] = item.get("change_id") or _make_change_id(item)

            file_path = str(item.get("file_path", ""))
            risk = str(item.get("risk_level", "HIGH")).upper()

            if self._is_restricted(file_path):
                item["approved"] = False
                item["gate_reason"] = "Blocked: restricted directory (governance policy)."
                categorized["blocked"].append(item)
                continue

            if too_many_files:
                item["approved"] = False
                item["gate_reason"] = (
                    f"Approval required: run touches {len(touched_files)} files "
                    f"(max_files_per_sync={self.max_files_per_sync})."
                )
                categorized["approval_required"].append(item)
                continue

            if risk in self.require_approval_for:
                item["approved"] = False
                item["gate_reason"] = f"Approval required by policy for risk_level={risk}."
                categorized["approval_required"].append(item)
                continue

            if risk == "LOW":
                item["approved"] = self.auto_approve_low_risk
                item["gate_reason"] = (
                    "Auto-approved low-risk change."
                    if item["approved"]
                    else "Low-risk: awaiting approval."
                )

                if item["approved"]:
                    categorized["autonomous"].append(item)
                else:
                    categorized["approval_required"].append(item)
                continue

            item["approved"] = False
            item["gate_reason"] = (
                f"Unrecognized risk_level='{risk}', defaulting to approval required."
            )
            categorized["approval_required"].append(item)

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
        Marks selected recommendations as approved and adds audit fields.
        """
        updated: List[Dict[str, Any]] = []

        for rec in recommendations:
            item = dict(rec)
            item["change_id"] = item.get("change_id") or _make_change_id(item)

            if item["change_id"] in approved_change_ids:
                item["approved"] = True
                item["approved_by"] = user_id
                item["approved_at"] = datetime.now().isoformat()
                self.validate_human_signature(user_id=user_id, change_id=item["change_id"])
            else:
                item["approved"] = bool(item.get("approved", False))

            updated.append(item)

        return updated

    def validate_human_signature(self, user_id: str, change_id: str) -> bool:
        """
        Writes a minimal audit trail entry.
        In production, this would write to a persistent log or database.
        """
        logger.info("AUDIT: user=%s approved change_id=%s", user_id, change_id)
        return True

    def _is_restricted(self, path: str) -> bool:
        if not path:
            return False

        normalized_path = path.replace("\\", "/")

        for restricted_dir in self.restricted_directories:
            rule = str(restricted_dir).replace("\\", "/").rstrip("/")
            if not rule:
                continue

            if normalized_path.startswith(rule) or normalized_path.startswith(rule.lstrip("/")):
                return True

        return False