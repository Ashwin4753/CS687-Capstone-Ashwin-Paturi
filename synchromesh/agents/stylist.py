import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    from google.adk import Agent  # type: ignore
except Exception:
    Agent = None


@dataclass
class Recommendation:
    file_path: str
    line: int
    kind: str  # COLOR | SIZE | INLINE_STYLE | UNKNOWN
    original_value: str
    proposed_token: str
    replacement_text: str
    risk_level: str  # LOW | MEDIUM | HIGH
    risk_reason: str
    reasoning: str
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    snippet: str = ""


class StylistAgent:
    """
    Stylist Agent

    Responsibilities:
    - Compare ghost styles against authoritative design tokens
    - Produce structured recommendations for governed synchronization
    - Assign bounded-autonomy risk tiers
    - Provide stable local reasoning strings for demo/runtime reliability

    Notes:
    - Approximate matching is currently implemented for colors only.
    - Exact value matches are treated as LOW risk.
    """

    def __init__(self) -> None:
        # For demo/runtime stability we do not instantiate ADK directly here,
        # since constructor APIs vary across versions.
        self.agent = None

    def _adk_call(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Safe fallback reasoning generator for demo/runtime stability.
        """
        context = context or {}

        if "matched_token" in context:
            return (
                f"Exact token match identified for value '{context.get('original_value', '')}', "
                f"so '{context.get('matched_token', '')}' is considered a safe substitution."
            )

        if "approx_token" in context:
            return (
                f"Approximate token match found for value '{context.get('original_value', '')}'. "
                f"The recommendation '{context.get('approx_token', '')}' is plausible but should be reviewed."
            )

        if context.get("snippet"):
            return (
                "This finding may require manual review because the detected style appears "
                "structural, unmatched, or insufficiently reliable for autonomous replacement."
            )

        return "Recommendation generated."

    @staticmethod
    def _make_change_id(rec: Dict[str, Any]) -> str:
        key = (
            f"{rec.get('file_path', '')}|"
            f"{rec.get('line', '')}|"
            f"{rec.get('original_value', '')}|"
            f"{rec.get('replacement_text', '')}"
        )
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

    def detect_drift(
        self,
        ghost_styles: List[Dict[str, Any]],
        figma_tokens: Dict[str, Any],
        token_format: str = "var(--{token})",
    ) -> List[Dict[str, Any]]:
        """
        Converts Archaeologist findings into governed recommendations.

        Inputs:
        - ghost_styles: output of ArchaeologistAgent.find_ghost_styles()
        - figma_tokens: token map, ideally {token_name: token_value}
        - token_format: how tokens should be rendered in replacement text

        Returns:
        - List[Dict[str, Any]] ready for ApprovalGate, Syncer, UI, and evaluation
        """
        value_to_token = self._build_value_to_token_map(figma_tokens)
        token_to_value = self._build_token_to_value_map(figma_tokens)

        recommendations: List[Recommendation] = []

        for finding in ghost_styles:
            file_path = str(finding.get("file_path", ""))
            line = int(finding.get("line", 0))
            kind_raw = finding.get("kind", finding.get("type", ""))
            original_value = str(finding.get("value", "")).strip()
            snippet = str(finding.get("snippet", ""))

            span_start = finding.get("span_start")
            span_end = finding.get("span_end")

            kind = self._normalize_kind(kind_raw)

            # HIGH: inline style blocks
            if kind == "INLINE_STYLE":
                recommendations.append(
                    Recommendation(
                        file_path=file_path,
                        line=line,
                        kind=kind,
                        original_value=original_value,
                        proposed_token="N/A",
                        replacement_text="N/A",
                        risk_level="HIGH",
                        risk_reason="Inline style block likely requires structural refactor or manual review.",
                        reasoning=self._adk_call(
                            "Write a concise governance explanation for why this inline style should be treated as HIGH risk.",
                            context={
                                "file_path": file_path,
                                "line": line,
                                "snippet": snippet[:160],
                            },
                        ),
                        span_start=span_start,
                        span_end=span_end,
                        snippet=snippet,
                    )
                )
                continue

            # HIGH: unknown finding types
            if kind == "UNKNOWN":
                recommendations.append(
                    Recommendation(
                        file_path=file_path,
                        line=line,
                        kind=kind,
                        original_value=original_value,
                        proposed_token="UNKNOWN_TOKEN",
                        replacement_text="N/A",
                        risk_level="HIGH",
                        risk_reason="Unsupported or unknown finding type; requires manual review.",
                        reasoning=self._adk_call(
                            "Write a concise explanation for why this unsupported finding should be treated as HIGH risk.",
                            context={
                                "file_path": file_path,
                                "line": line,
                                "original_value": original_value,
                                "snippet": snippet[:160],
                            },
                        ),
                        span_start=span_start,
                        span_end=span_end,
                        snippet=snippet,
                    )
                )
                continue

            normalized = self._normalize_value(original_value, kind)

            # LOW: exact token match
            exact_token = value_to_token.get(normalized)
            if exact_token:
                replacement_text = token_format.format(token=exact_token)
                recommendations.append(
                    Recommendation(
                        file_path=file_path,
                        line=line,
                        kind=kind,
                        original_value=original_value,
                        proposed_token=exact_token,
                        replacement_text=replacement_text,
                        risk_level="LOW",
                        risk_reason="Exact token value match (safe token substitution).",
                        reasoning=self._adk_call(
                            "Produce a concise reasoning sentence for a LOW-risk exact token substitution.",
                            context={
                                "file_path": file_path,
                                "line": line,
                                "original_value": original_value,
                                "normalized_value": normalized,
                                "matched_token": exact_token,
                                "replacement_text": replacement_text,
                            },
                        ),
                        span_start=span_start,
                        span_end=span_end,
                        snippet=snippet,
                    )
                )
                continue

            # MEDIUM: approximate color match only
            approx_token: Optional[str] = None
            approx_score: Optional[float] = None

            if kind == "COLOR":
                approx_token, approx_score = self._approximate_color_match(
                    normalized_value=normalized,
                    token_to_value=token_to_value,
                )

            if approx_token is not None and approx_score is not None and approx_score >= 0.92:
                replacement_text = token_format.format(token=approx_token)
                recommendations.append(
                    Recommendation(
                        file_path=file_path,
                        line=line,
                        kind=kind,
                        original_value=original_value,
                        proposed_token=approx_token,
                        replacement_text=replacement_text,
                        risk_level="MEDIUM",
                        risk_reason=f"Close color match detected (similarity={approx_score:.2f}); approval required.",
                        reasoning=self._adk_call(
                            "Write a short governance explanation for a MEDIUM-risk recommendation caused by approximate color matching.",
                            context={
                                "file_path": file_path,
                                "line": line,
                                "original_value": original_value,
                                "normalized_value": normalized,
                                "approx_token": approx_token,
                                "similarity": approx_score,
                                "replacement_text": replacement_text,
                            },
                        ),
                        span_start=span_start,
                        span_end=span_end,
                        snippet=snippet,
                    )
                )
                continue

            # HIGH: unknown / unmatched token
            recommendations.append(
                Recommendation(
                    file_path=file_path,
                    line=line,
                    kind=kind,
                    original_value=original_value,
                    proposed_token="UNKNOWN_TOKEN",
                    replacement_text="N/A",
                    risk_level="HIGH",
                    risk_reason="No matching design token found; possible drift or missing token definition.",
                    reasoning=self._adk_call(
                        "Write a short governance explanation for a HIGH-risk unmatched drift finding.",
                        context={
                            "file_path": file_path,
                            "line": line,
                            "original_value": original_value,
                            "normalized_value": normalized,
                            "snippet": snippet[:160],
                        },
                    ),
                    span_start=span_start,
                    span_end=span_end,
                    snippet=snippet,
                )
            )

        out = [asdict(rec) for rec in recommendations]

        for rec in out:
            rec["change_id"] = self._make_change_id(rec)
            rec["token_found"] = rec.get("proposed_token") not in {"UNKNOWN_TOKEN", "N/A"}

            risk = str(rec.get("risk_level", "HIGH")).upper()
            if risk == "LOW":
                rec["confidence_score"] = 0.95
            elif risk == "MEDIUM":
                rec["confidence_score"] = 0.75
            else:
                rec["confidence_score"] = 0.55

        return out

    @staticmethod
    def _normalize_kind(kind_raw: str) -> str:
        kind = (kind_raw or "").upper()
        if "COLOR" in kind:
            return "COLOR"
        if "SIZE" in kind:
            return "SIZE"
        if "INLINE" in kind:
            return "INLINE_STYLE"
        return "UNKNOWN"

    def _build_token_to_value_map(self, figma_tokens: Dict[str, Any]) -> Dict[str, str]:
        """
        Supports both:
        - {token_name: value}
        - nested token dicts
        """
        flat: Dict[str, str] = {}

        def walk(prefix: str, obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    walk(f"{prefix}{key}." if prefix else f"{key}.", value)
            else:
                token_name = prefix[:-1] if prefix.endswith(".") else prefix
                flat[token_name] = str(obj)

        if any(isinstance(v, dict) for v in figma_tokens.values()):
            walk("", figma_tokens)
        else:
            for key, value in figma_tokens.items():
                flat[str(key)] = str(value)

        return flat

    def _build_value_to_token_map(self, figma_tokens: Dict[str, Any]) -> Dict[str, str]:
        """
        Builds normalized value -> token lookup.

        If multiple tokens normalize to the same value, the first one encountered wins.
        This keeps behavior deterministic enough for capstone/demo purposes.
        """
        token_to_value = self._build_token_to_value_map(figma_tokens)
        value_to_token: Dict[str, str] = {}

        for token, value in token_to_value.items():
            norm_color = self._normalize_color(value)
            if norm_color and norm_color not in value_to_token:
                value_to_token[norm_color] = token

            norm_size = self._normalize_size(value)
            if norm_size and norm_size not in value_to_token:
                value_to_token[norm_size] = token

        return value_to_token

    def _normalize_value(self, value: str, kind: str) -> str:
        if kind == "COLOR":
            normalized = self._normalize_color(value)
            return normalized or value.strip().lower()

        if kind == "SIZE":
            normalized = self._normalize_size(value)
            return normalized or value.strip().lower()

        return value.strip().lower()

    @staticmethod
    def _normalize_color(value: str) -> Optional[str]:
        raw = value.strip().lower()

        # Normalize hex (#fff -> #ffffff)
        if raw.startswith("#") and len(raw) in (4, 7):
            if len(raw) == 4:
                r, g, b = raw[1], raw[2], raw[3]
                return f"#{r}{r}{g}{g}{b}{b}"
            return raw

        # Normalize rgb()/rgba() to hex (alpha ignored for parity matching)
        if raw.startswith("rgb"):
            nums = []
            current = ""
            for ch in raw:
                if ch.isdigit() or ch == ".":
                    current += ch
                else:
                    if current:
                        nums.append(current)
                        current = ""
            if current:
                nums.append(current)

            if len(nums) >= 3:
                try:
                    r = max(0, min(255, int(float(nums[0]))))
                    g = max(0, min(255, int(float(nums[1]))))
                    b = max(0, min(255, int(float(nums[2]))))
                    return f"#{r:02x}{g:02x}{b:02x}"
                except Exception:
                    return None

        return None

    @staticmethod
    def _normalize_size(value: str) -> Optional[str]:
        raw = value.strip().lower()

        import re
        match = re.match(r"^(\d+(?:\.\d+)?)(px|rem|em|%)$", raw)
        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2)

        if number.is_integer():
            return f"{int(number)}{unit}"
        return f"{number}{unit}"

    def _approximate_color_match(
        self,
        normalized_value: str,
        token_to_value: Dict[str, str],
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Returns (token, similarity) where similarity is in [0, 1].
        Approximate matching is only used for color recommendations.
        """
        target_rgb = self._hex_to_rgb(normalized_value)
        if target_rgb is None:
            return None, None

        best_token: Optional[str] = None
        best_similarity = 0.0

        for token, raw_value in token_to_value.items():
            normalized_token_value = self._normalize_color(raw_value)
            if not normalized_token_value:
                continue

            token_rgb = self._hex_to_rgb(normalized_token_value)
            if not token_rgb:
                continue

            similarity = self._rgb_similarity(target_rgb, token_rgb)
            if similarity > best_similarity:
                best_similarity = similarity
                best_token = token

        if best_token is not None:
            return best_token, best_similarity

        return None, None

    @staticmethod
    def _hex_to_rgb(hex_value: str) -> Optional[Tuple[int, int, int]]:
        raw = hex_value.strip().lower()
        if not (raw.startswith("#") and len(raw) == 7):
            return None

        try:
            return (
                int(raw[1:3], 16),
                int(raw[3:5], 16),
                int(raw[5:7], 16),
            )
        except Exception:
            return None

    @staticmethod
    def _rgb_similarity(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
        """
        Euclidean RGB similarity normalized to [0, 1].
        """
        import math

        dr = a[0] - b[0]
        dg = a[1] - b[1]
        db = a[2] - b[2]

        distance = math.sqrt(dr * dr + dg * dg + db * db)
        max_distance = math.sqrt(255 * 255 * 3)

        return 1.0 - (distance / max_distance)