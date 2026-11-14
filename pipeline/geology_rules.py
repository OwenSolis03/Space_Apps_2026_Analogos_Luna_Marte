"""Shared geological taxonomy, GLiM tables, similarity matrix, and Moon/Mars rules (T14)."""

from __future__ import annotations

import logging
import re
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)

GEO_CLASSES: tuple[str, ...] = (
    "VOLCANIC_BASIC",
    "VOLCANIC_OTHER",
    "PYROCLASTIC",
    "CRYSTALLINE",
    "IMPACT",
    "SEDIMENTARY",
    "EVAPORITE",
    "ICE",
)

GLIM_CODES: dict[int, str] = {
    1: "su",
    2: "vb",
    3: "ss",
    4: "pb",
    5: "sm",
    6: "sc",
    7: "va",
    8: "mt",
    9: "pa",
    10: "vi",
    11: "wb",
    12: "py",
    13: "pi",
    14: "ev",
    15: "nd",
    16: "ig",
}

VALID_GLIM_INT_CODES: set[int] = {
    code_int for code_int, short in GLIM_CODES.items() if short not in ("wb", "nd")
}

GLIM_TO_CLASS: dict[str, str | None] = {
    "vb": "VOLCANIC_BASIC",
    "va": "VOLCANIC_OTHER",
    "vi": "VOLCANIC_OTHER",
    "py": "PYROCLASTIC",
    "pa": "CRYSTALLINE",
    "pb": "CRYSTALLINE",
    "pi": "CRYSTALLINE",
    "mt": "CRYSTALLINE",
    "ss": "SEDIMENTARY",
    "sm": "SEDIMENTARY",
    "sc": "SEDIMENTARY",
    "su": "SEDIMENTARY",
    "ev": "EVAPORITE",
    "ig": "ICE",
    "wb": None,
    "nd": None,
}

_OFF_DIAGONAL_SIMILARITIES: dict[tuple[str, str], float] = {
    ("VOLCANIC_BASIC", "PYROCLASTIC"): 0.6,
    ("VOLCANIC_BASIC", "VOLCANIC_OTHER"): 0.5,
    ("VOLCANIC_OTHER", "PYROCLASTIC"): 0.5,
    ("CRYSTALLINE", "IMPACT"): 0.4,
    ("SEDIMENTARY", "EVAPORITE"): 0.6,
    ("SEDIMENTARY", "IMPACT"): 0.2,
}


class SimilarityMatrix(dict):
    """Symmetric class similarity matrix supporting matrix[a][b] and matrix[(a, b)]."""

    def __getitem__(self, key: object):
        if isinstance(key, tuple) and len(key) == 2:
            a, b = key
            return super().__getitem__(a)[b]
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, tuple) and len(key) == 2:
            a, b = key
            return super().__contains__(a) and b in super().__getitem__(a)
        return super().__contains__(key)

    def get(self, key: object, default: object = None):
        if isinstance(key, tuple) and len(key) == 2:
            a, b = key
            row = super().get(a)
            if isinstance(row, dict):
                return row.get(b, default)
            return default
        return super().get(key, default)


def _build_similarity_matrix() -> SimilarityMatrix:
    mat = SimilarityMatrix()
    for c1 in GEO_CLASSES:
        mat[c1] = {c2: (1.0 if c1 == c2 else 0.0) for c2 in GEO_CLASSES}
    for (c1, c2), val in _OFF_DIAGONAL_SIMILARITIES.items():
        mat[c1][c2] = float(val)
        mat[c2][c1] = float(val)
    return mat


GEO_SIMILARITY: SimilarityMatrix = _build_similarity_matrix()


def geology_similarity(class_a: str | None, class_b: str | None) -> float:
    """Return pairwise similarity in [0, 1] between two GEO_CLASSES, or NaN if either is null."""
    if class_a is None or class_b is None or pd.isna(class_a) or pd.isna(class_b):
        return float("nan")
    a = str(class_a).strip()
    b = str(class_b).strip()
    if a not in GEO_SIMILARITY or b not in GEO_SIMILARITY[a]:
        return float("nan")
    return float(GEO_SIMILARITY[a][b])


# Ordered keyword rules per body: (assigned_class, keywords, rule_label).
# Word boundaries avoid false positives such as "edifice" matching "ice".
MOON_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("VOLCANIC_BASIC", ("mare", "maria"), "mare / maria"),
    ("PYROCLASTIC", ("dark mantle", "pyroclastic"), "dark mantle / pyroclastic"),
    ("IMPACT", ("crater", "basin", "ejecta", "impact"), "crater / basin / ejecta / impact"),
    ("CRYSTALLINE", ("terra", "highland", "plains"), "terra / highland / plains"),
)

MARS_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("ICE", ("polar", "ice", "layered deposit"), "polar / ice / layered deposit"),
    (
        "VOLCANIC_BASIC",
        ("volcanic", "volcano", "lava", "edifice", "tharsis"),
        "volcanic / volcano / lava / edifice / Tharsis",
    ),
    ("IMPACT", ("impact", "crater"), "impact / crater"),
    (
        "SEDIMENTARY",
        (
            "lowland",
            "basin",
            "transition",
            "plains",
            "sedimentary",
            "vastitas",
            "apron",
            "channel",
        ),
        "lowland / basin / transition / plains / sedimentary / Vastitas / apron / channel",
    ),
    ("IMPACT", ("highland",), "highland"),
)


def _compile_patterns(
    rules: Iterable[tuple[str, tuple[str, ...], str]],
) -> list[tuple[str, re.Pattern[str], str]]:
    compiled: list[tuple[str, re.Pattern[str], str]] = []
    for geo_class, keywords, label in rules:
        parts = [rf"\b{re.escape(kw)}(?:s|es)?\b" for kw in keywords]
        pattern = re.compile("|".join(parts), flags=re.IGNORECASE)
        compiled.append((geo_class, pattern, label))
    return compiled


_COMPILED_MOON_RULES = _compile_patterns(MOON_RULES)
_COMPILED_MARS_RULES = _compile_patterns(MARS_RULES)


def classify_unit(body: str, text: str | None) -> tuple[str | None, str]:
    """Map a Moon or Mars unit name/description to (geo_class, matched_rule)."""
    body_norm = body.strip().capitalize()
    raw_text = "" if text is None or pd.isna(text) else str(text)

    if body_norm == "Moon":
        for geo_class, pattern, label in _COMPILED_MOON_RULES:
            if pattern.search(raw_text):
                return geo_class, label
        logger.warning("Moon unit mapped by default rule -> CRYSTALLINE: %r", raw_text[:120])
        return "CRYSTALLINE", "default"

    if body_norm == "Mars":
        for geo_class, pattern, label in _COMPILED_MARS_RULES:
            if pattern.search(raw_text):
                return geo_class, label
        logger.warning("Mars unit mapped by default rule -> null: %r", raw_text[:120])
        return None, "default"

    raise ValueError(f"Unsupported planetary body for unit classification: {body!r}")


def classify_unit_table(
    df: pd.DataFrame,
    body: str,
    text_cols: Iterable[str] = ("unit_name", "description", "unit"),
) -> pd.DataFrame:
    """Apply ordered unit keyword rules to every row in a unit summary DataFrame."""
    out = df.copy()
    cols = [c for c in text_cols if c in out.columns]
    if not cols:
        raise KeyError(
            f"None of {list(text_cols)} found in unit table columns {list(out.columns)}"
        )

    classes: list[str | None] = []
    rules: list[str] = []
    for _, row in out.iterrows():
        parts = [str(row[c]).strip() for c in cols if row[c] is not None and pd.notna(row[c])]
        combined = " | ".join(p for p in parts if p)
        geo_class, rule = classify_unit(body, combined)
        classes.append(geo_class)
        rules.append(rule)

    out["geo_class"] = pd.Series(classes, index=out.index, dtype="string")
    out["rule_matched"] = pd.Series(rules, index=out.index, dtype="string")
    return out
