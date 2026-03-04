from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    from google_adk import Agent
except Exception as e:
    raise ImportError(
        "google_adk is required (core functionality). "
        "Install/enable Google ADK in this environment before running SynchroMesh."
    ) from e

@dataclass
class Recommendation:
    file_path: str
    line: int
    kind: str  # COLOR | SIZE | INLINE_STYLE
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
    - Compares ghost styles against authoritative tokens
    - Produces recommendations with bounded autonomy risk tiers
    - Uses ADK for explainable reasoning output (ADK is core)
    """

    def __init__(self) -> None:
        self.agent = Agent(
            name="Stylist",
            instructions=(
                "You are a Design System Expert.\n"
                "Given detected ghost styles and Figma design tokens, match values to tokens.\n"
                "Output structured recommendations. Use bounded autonomy:\n"
                "LOW = safe token swap (exact match), MEDIUM = close match (needs approval),\n"
                "HIGH = unknown/inline/structural.\n"
                "Provide concise reasoning suitable for a governance dashboard.\n"
            ),
        )

    # ---------- ADK call helper ----------
    def _adk_call(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        payload = {"prompt": prompt, "context": context or {}}

        for method_name in ("run", "invoke", "chat"):
            fn = getattr(self.agent, method_name, None)
            if callable(fn):
                try:
                    result = fn(payload)  # type: ignore[misc]
                    return self._stringify_adk_result(result)
                except TypeError:
                    result = fn(prompt)  # type: ignore[misc]
                    return self._stringify_adk_result(result)

        if callable(self.agent):
            result = self.agent(payload)  # type: ignore[misc]
            return self._stringify_adk_result(result)

        raise RuntimeError("Unable to execute ADK Agent; supported call methods not found.")

    @staticmethod
    def _stringify_adk_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            for k in ("output", "text", "message", "content"):
                if k in result and isinstance(result[k], str):
                    return result[k]
            return str(result)
        for attr in ("output", "text", "message", "content"):
            val = getattr(result, attr, None)
            if isinstance(val, str):
                return val
        return str(result)

    # ---------- public API ----------
    def detect_drift(
        self,
        ghost_styles: List[Dict[str, Any]],
        figma_tokens: Dict[str, Any],
        token_format: str = "var(--{token})",
    ) -> List[Dict[str, Any]]:
        """
        ghost_styles: output of ArchaeologistAgent.find_ghost_styles()
        figma_tokens: dict of tokens, ideally {token_name: token_value}
        token_format: how replacements are rendered, e.g. "var(--{token})" or "{token}"
        """
        value_to_token = self._build_value_to_token_map(figma_tokens)
        token_to_value = self._build_token_to_value_map(figma_tokens)

        recs: List[Recommendation] = []
        for gs in ghost_styles:
            file_path = gs.get("file_path", "")
            line = int(gs.get("line", 0))
            kind_raw = gs.get("kind", gs.get("type", ""))
            original = str(gs.get("value", "")).strip()
            snippet = str(gs.get("snippet", ""))

            span_start = gs.get("span_start")
            span_end = gs.get("span_end")

            kind = self._normalize_kind(kind_raw)

            # Inline styles are HIGH by policy (recommendation-only)
            if kind == "INLINE_STYLE":
                recs.append(
                    Recommendation(
                        file_path=file_path,
                        line=line,
                        kind=kind,
                        original_value=original,
                        proposed_token="N/A",
                        replacement_text="N/A",
                        risk_level="HIGH",
                        risk_reason="Inline style block likely needs structural refactor / manual review.",
                        reasoning=self._adk_call(
                            "Write a 1-2 sentence governance explanation for why inline styles are high-risk.",
                            context={"file_path": file_path, "line": line, "snippet": snippet[:160]},
                        ),
                        span_start=span_start,
                        span_end=span_end,
                        snippet=snippet,
                    )
                )
                continue

            # 1) Try exact match (LOW)
            normalized = self._normalize_value(original, kind)
            exact_token = value_to_token.get(normalized)

            if exact_token:
                recs.append(
                    Recommendation(
                        file_path=file_path,
                        line=line,
                        kind=kind,
                        original_value=original,
                        proposed_token=exact_token,
                        replacement_text=token_format.format(token=exact_token),
                        risk_level="LOW",
                        risk_reason="Exact token value match (safe token substitution).",
                        reasoning=self._adk_call(
                            "Produce a concise reasoning sentence for a LOW-risk token substitution.",
                            context={
                                "original_value": original,
                                "normalized_value": normalized,
                                "matched_token": exact_token,
                                "replacement_text": token_format.format(token=exact_token),
                            },
                        ),
                        span_start=span_start,
                        span_end=span_end,
                        snippet=snippet,
                    )
                )
                continue

            # 2) Try approximate match for colors (MEDIUM)
            approx_token, approx_score = None, None
            if kind == "COLOR":
                approx_token, approx_score = self._approximate_color_match(
                    normalized_value=normalized,
                    token_to_value=token_to_value,
                )

            if approx_token and approx_score is not None and approx_score >= 0.92:
                recs.append(
                    Recommendation(
                        file_path=file_path,
                        line=line,
                        kind=kind,
                        original_value=original,
                        proposed_token=approx_token,
                        replacement_text=token_format.format(token=approx_token),
                        risk_level="MEDIUM",
                        risk_reason=f"Close color match (similarity={approx_score:.2f}); requires approval.",
                        reasoning=self._adk_call(
                            "Write a short governance explanation for a MEDIUM-risk recommendation "
                            "due to approximate token match.",
                            context={
                                "original_value": original,
                                "normalized_value": normalized,
                                "approx_token": approx_token,
                                "similarity": approx_score,
                                "replacement_text": token_format.format(token=approx_token),
                            },
                        ),
                        span_start=span_start,
                        span_end=span_end,
                        snippet=snippet,
                    )
                )
                continue

            # 3) Unknown token (HIGH)
            recs.append(
                Recommendation(
                    file_path=file_path,
                    line=line,
                    kind=kind,
                    original_value=original,
                    proposed_token="UNKNOWN_TOKEN",
                    replacement_text="N/A",
                    risk_level="HIGH",
                    risk_reason="No matching token found; potential design drift or missing token definition.",
                    reasoning=self._adk_call(
                        "Write a short governance explanation for a HIGH-risk drift finding with no token match.",
                        context={
                            "original_value": original,
                            "normalized_value": normalized,
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

        return [asdict(r) for r in recs]

    # ---------- internals ----------
    @staticmethod
    def _normalize_kind(kind_raw: str) -> str:
        k = (kind_raw or "").upper()
        if "COLOR" in k:
            return "COLOR"
        if "SIZE" in k:
            return "SIZE"
        if "INLINE" in k:
            return "INLINE_STYLE"
        return "UNKNOWN"

    def _build_token_to_value_map(self, figma_tokens: Dict[str, Any]) -> Dict[str, str]:
        """
        Supports either:
          - {token_name: value}
          - {category: {token_name: value}} (nested)
        """
        flat: Dict[str, str] = {}

        def walk(prefix: str, obj: Any) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    walk(f"{prefix}{k}." if prefix else f"{k}.", v)
            else:
                # leaf value
                token_name = prefix[:-1] if prefix.endswith(".") else prefix
                flat[token_name] = str(obj)

        # Heuristic: if most values are dict => nested
        if any(isinstance(v, dict) for v in figma_tokens.values()):
            walk("", figma_tokens)
        else:
            for k, v in figma_tokens.items():
                flat[str(k)] = str(v)

        return flat

    def _build_value_to_token_map(self, figma_tokens: Dict[str, Any]) -> Dict[str, str]:
        token_to_value = self._build_token_to_value_map(figma_tokens)
        value_to_token: Dict[str, str] = {}
        for token, value in token_to_value.items():
            # store normalized for COLOR/SIZE in a broad way (we’ll normalize per kind during lookup)
            # For value_to_token we normalize color-ish strings and keep raw sizes too.
            norm_color = self._normalize_color(value)
            if norm_color:
                value_to_token[norm_color] = token
            norm_size = self._normalize_size(value)
            if norm_size:
                value_to_token[norm_size] = token
        return value_to_token

    def _normalize_value(self, value: str, kind: str) -> str:
        if kind == "COLOR":
            norm = self._normalize_color(value)
            return norm or value.strip().lower()
        if kind == "SIZE":
            norm = self._normalize_size(value)
            return norm or value.strip().lower()
        return value.strip().lower()

    @staticmethod
    def _normalize_color(value: str) -> Optional[str]:
        v = value.strip().lower()

        # hex normalize (#fff -> #ffffff)
        if v.startswith("#") and len(v) in (4, 7):
            if len(v) == 4:
                r, g, b = v[1], v[2], v[3]
                return f"#{r}{r}{g}{g}{b}{b}"
            return v

        # rgb/rgba to hex (ignore alpha for parity matching)
        if v.startswith("rgb"):
            nums = []
            cur = ""
            for ch in v:
                if ch.isdigit() or ch == ".":
                    cur += ch
                else:
                    if cur:
                        nums.append(cur)
                        cur = ""
            if cur:
                nums.append(cur)

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
        v = value.strip().lower()
        # Normalize "12px" "12.0px" -> "12px", "1.50rem" -> "1.5rem"
        import re

        m = re.match(r"^(\d+(?:\.\d+)?)(px|rem|em|%)$", v)
        if not m:
            return None
        num = float(m.group(1))
        unit = m.group(2)
        # Remove trailing .0
        if num.is_integer():
            return f"{int(num)}{unit}"
        return f"{num}{unit}"

    def _approximate_color_match(
        self,
        normalized_value: str,
        token_to_value: Dict[str, str],
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Returns (token, similarity) where similarity is 0..1.
        Uses simple RGB distance; capstone-appropriate.
        """
        target = self._hex_to_rgb(normalized_value)
        if target is None:
            return None, None

        best_token = None
        best_sim = 0.0

        for token, raw_val in token_to_value.items():
            norm = self._normalize_color(raw_val)
            if not norm:
                continue
            rgb = self._hex_to_rgb(norm)
            if not rgb:
                continue
            sim = self._rgb_similarity(target, rgb)
            if sim > best_sim:
                best_sim = sim
                best_token = token

        return best_token, best_sim if best_token else (None, None)

    @staticmethod
    def _hex_to_rgb(hexv: str) -> Optional[Tuple[int, int, int]]:
        h = hexv.strip().lower()
        if not (h.startswith("#") and len(h) == 7):
            return None
        try:
            return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        except Exception:
            return None

    @staticmethod
    def _rgb_similarity(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
        # Euclidean distance normalized to [0,1]
        import math

        dr = a[0] - b[0]
        dg = a[1] - b[1]
        db = a[2] - b[2]
        dist = math.sqrt(dr * dr + dg * dg + db * db)
        max_dist = math.sqrt(255 * 255 * 3)
        return 1.0 - (dist / max_dist)