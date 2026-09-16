from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

SEPARATOR_RE = re.compile(r"[\s._-]+")
NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
EXPLICIT_REV_RE = re.compile(
    r"(?i)(?:^|[\s._-])(?:REV(?:ISION)?|R)[\s._-]*([A-Z]|\d{1,4})(?=$|[\s._-])"
)

FOLDER_RULES: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("released", 500, ("released", "release", "production", "approved")),
    ("current", 400, ("current", "engineering", "design")),
    ("supplier", 300, ("supplier", "vendor")),
    ("wip", 180, ("wip", "work in progress", "draft")),
    ("archive", 50, ("archive", "archived", "obsolete", "old")),
)

DESCRIPTOR_TOKENS = {
    "DRAWING",
    "DWG",
    "MODEL",
    "CAD",
    "STEP",
    "STP",
    "PDF",
    "DXF",
    "SPEC",
    "SPECIFICATION",
}


@dataclass(frozen=True)
class NormalizedCode:
    original: str
    cleaned: str
    normalized: str
    compact: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class ParsedFilename:
    normalized_filename: str
    normalized_stem: str
    compact_stem: str
    parsed_code: str
    compact_code: str
    revision_raw: Optional[str]
    revision_rank: int
    tokens: tuple[str, ...]
    folder_class: str
    folder_priority: int


def _strip_supported_extension(value: str) -> str:
    suffix = Path(value).suffix.lower()
    if suffix in {
        ".stp", ".step", ".pdf", ".dxf", ".doc", ".docx", ".xls", ".xlsx",
        ".ppt", ".pptx", ".md", ".txt", ".html", ".htm",
    }:
        return value[: -len(suffix)]
    return value


def normalize_code(value: str) -> NormalizedCode:
    original = value
    cleaned = value.strip().strip('"').strip("'")
    cleaned = _strip_supported_extension(cleaned)

    if re.fullmatch(r"\d+\.0", cleaned):
        cleaned = cleaned[:-2]

    normalized = SEPARATOR_RE.sub("-", cleaned.upper()).strip("-")
    compact = NON_ALNUM_RE.sub("", cleaned.upper())
    tokens = tuple(token for token in NON_ALNUM_RE.split(cleaned.upper()) if token)
    return NormalizedCode(
        original=original,
        cleaned=cleaned,
        normalized=normalized,
        compact=compact,
        tokens=tokens,
    )


def revision_rank(value: Optional[str]) -> int:
    if not value:
        return 0
    raw = value.upper()
    if raw.isdigit():
        return int(raw)
    if len(raw) == 1 and "A" <= raw <= "Z":
        return 1000 + (ord(raw) - ord("A") + 1)
    return 0


def classify_folder(path: str) -> tuple[str, int]:
    lower = path.replace("\\", "/").lower()
    parts = [part for part in lower.split("/") if part]

    for folder_class, priority, markers in FOLDER_RULES:
        for marker in markers:
            pattern = re.compile(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])")
            if any(pattern.search(part) for part in parts):
                return folder_class, priority

    return "normal", 250


def _remove_revision(stem: str, match: re.Match[str]) -> str:
    start, end = match.span()
    before = stem[:start]
    after = stem[end:]
    combined = f"{before}{after}".strip(" ._-")
    return combined or stem


def _probable_code(stem_without_revision: str) -> str:
    tokens = [token for token in NON_ALNUM_RE.split(stem_without_revision.upper()) if token]
    while tokens and tokens[-1] in DESCRIPTOR_TOKENS:
        tokens.pop()

    if not tokens:
        return stem_without_revision

    return "-".join(tokens)


def parse_filename(filename: str, full_path: str) -> ParsedFilename:
    stem = Path(filename).stem
    rev_match = EXPLICIT_REV_RE.search(stem)
    revision = rev_match.group(1).upper() if rev_match else None
    code_stem = _remove_revision(stem, rev_match) if rev_match else stem
    probable_code = _probable_code(code_stem)

    normalized_filename = SEPARATOR_RE.sub("-", filename.upper()).strip("-")
    normalized_stem = SEPARATOR_RE.sub("-", stem.upper()).strip("-")
    compact_stem = NON_ALNUM_RE.sub("", stem.upper())
    parsed_code = SEPARATOR_RE.sub("-", probable_code.upper()).strip("-")
    compact_code = NON_ALNUM_RE.sub("", probable_code.upper())
    tokens = tuple(token for token in NON_ALNUM_RE.split(stem.upper()) if token)
    folder_class, folder_priority = classify_folder(full_path)

    return ParsedFilename(
        normalized_filename=normalized_filename,
        normalized_stem=normalized_stem,
        compact_stem=compact_stem,
        parsed_code=parsed_code,
        compact_code=compact_code,
        revision_raw=revision,
        revision_rank=revision_rank(revision),
        tokens=tokens,
        folder_class=folder_class,
        folder_priority=folder_priority,
    )


def match_candidate(query: NormalizedCode, row: dict) -> tuple[Optional[str], int, str]:
    compact_stem = str(row.get("compact_stem") or "")
    compact_code = str(row.get("compact_code") or "")
    parsed_code = str(row.get("parsed_code") or "")
    normalized_stem = str(row.get("normalized_stem") or "")
    tokens = tuple(str(row.get("tokens") or "").split("|"))

    if query.compact and compact_code == query.compact:
        if parsed_code == query.normalized:
            return "exact", 600, "Exact part number"
        return "exact_normalized", 585, "Exact after separator/case normalization"

    if query.compact and compact_stem == query.compact:
        if normalized_stem == query.normalized:
            return "exact", 590, "Exact filename"
        return "exact_normalized", 580, "Exact after separator/case normalization"

    if query.normalized and normalized_stem == query.normalized:
        return "exact_normalized", 570, "Exact normalized filename"

    if query.compact and query.compact in tokens:
        return "token", 500, "Exact filename token"

    if query.compact and compact_stem.startswith(query.compact):
        return "variant", 430, "Part-number prefix / variant"

    if query.compact and query.compact in compact_stem:
        return "partial", 350, "Normalized substring match"

    return None, 0, ""


def ranking_key(query: NormalizedCode, row: dict) -> tuple:
    match_type, match_rank, _ = match_candidate(query, row)
    return (
        match_rank,
        int(row.get("folder_priority") or 0),
        int(row.get("revision_rank") or 0),
        float(row.get("modified_at") or 0),
        -len(str(row.get("filename") or "")),
        str(row.get("filename") or "").upper(),
    )


def explain_candidate(query: NormalizedCode, row: dict) -> dict:
    match_type, _, reason = match_candidate(query, row)
    return {
        "match_type": match_type,
        "match_reason": reason,
        "revision": row.get("revision_raw"),
        "folder_class": row.get("folder_class") or "normal",
    }


def _distance_limit(query: str) -> int:
    if len(query) < 5:
        return 0
    if len(query) <= 12:
        return 1
    return 2


def edit_distance(left: str, right: str, max_distance: int = 2) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > max_distance:
        return max_distance + 1

    previous = list(range(len(right) + 1))
    for i, char_left in enumerate(left, start=1):
        current = [i]
        row_min = i
        for j, char_right in enumerate(right, start=1):
            value = min(
                current[j - 1] + 1,
                previous[j] + 1,
                previous[j - 1] + (0 if char_left == char_right else 1),
            )
            current.append(value)
            row_min = min(row_min, value)
        if row_min > max_distance:
            return max_distance + 1
        previous = current
    return previous[-1]


def fuzzy_suggestions(query: NormalizedCode, candidates: Iterable[dict], limit: int = 3) -> list[dict]:
    if not query.compact:
        return []

    allowed = _distance_limit(query.compact)
    if allowed == 0:
        return []

    suggestions: list[tuple[tuple, dict]] = []
    for row in candidates:
        candidate = str(row.get("compact_code") or row.get("compact_stem") or "")
        if not candidate:
            continue

        if len(query.compact) >= 6 and candidate[:3] != query.compact[:3]:
            continue

        distance = edit_distance(query.compact, candidate, allowed)
        if distance > allowed:
            continue

        ratio = difflib.SequenceMatcher(a=query.compact, b=candidate).ratio()
        key = (
            -distance,
            ratio,
            int(row.get("folder_priority") or 0),
            int(row.get("revision_rank") or 0),
            float(row.get("modified_at") or 0),
        )
        suggestions.append((key, row))

    suggestions.sort(key=lambda item: item[0], reverse=True)
    output: list[dict] = []
    seen: set[str] = set()
    for _, row in suggestions:
        path = str(row.get("full_path") or "")
        if path in seen:
            continue
        seen.add(path)
        candidate = str(row.get("compact_code") or row.get("compact_stem") or "")
        distance = edit_distance(query.compact, candidate, allowed)
        output.append({
            "file_id": row["id"],
            "filename": row["filename"],
            "extension": row["extension"],
            "distance": distance,
            "reason": f"{distance}-character difference",
            "revision": row.get("revision_raw"),
            "folder_class": row.get("folder_class") or "normal",
        })
        if len(output) >= limit:
            break

    return output
