from __future__ import annotations

import html
import math
from pathlib import Path
from typing import List, Tuple

Point = Tuple[float, float]


def _read_pairs(path: Path) -> List[Tuple[str, str]]:
    lines = path.read_text(errors="ignore").splitlines()
    pairs = []
    i = 0
    while i + 1 < len(lines):
        pairs.append((lines[i].strip(), lines[i + 1].strip()))
        i += 2
    return pairs


def _entity_chunks(pairs: List[Tuple[str, str]]):
    in_entities = False
    current = None
    for code, value in pairs:
        if code == "2" and value.upper() == "ENTITIES":
            in_entities = True
            continue
        if in_entities and code == "0" and value.upper() == "ENDSEC":
            if current:
                yield current
            return
        if not in_entities:
            continue
        if code == "0":
            if current:
                yield current
            current = {"type": value.upper(), "pairs": []}
        elif current:
            current["pairs"].append((code, value))
    if current:
        yield current


def _float(v: str, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _values(entity, wanted: str) -> List[str]:
    return [v for c, v in entity["pairs"] if c == wanted]


def _first(entity, wanted: str, default="0") -> str:
    vals = _values(entity, wanted)
    return vals[0] if vals else default


def _bounds(points: List[Point]) -> Tuple[float, float, float, float]:
    if not points:
        return (0, 0, 100, 100)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    if abs(maxx - minx) < 1e-6:
        maxx += 50; minx -= 50
    if abs(maxy - miny) < 1e-6:
        maxy += 50; miny -= 50
    return minx, miny, maxx, maxy


def dxf_to_svg(path: Path, title: str = "DXF preview") -> str:
    pairs = _read_pairs(path)
    shapes: List[str] = []
    points: List[Point] = []

    for e in _entity_chunks(pairs):
        t = e["type"]
        if t == "LINE":
            x1, y1 = _float(_first(e, "10")), _float(_first(e, "20"))
            x2, y2 = _float(_first(e, "11")), _float(_first(e, "21"))
            points.extend([(x1, y1), (x2, y2)])
            shapes.append(f'<line x1="{x1}" y1="{-y1}" x2="{x2}" y2="{-y2}" />')
        elif t == "CIRCLE":
            x, y = _float(_first(e, "10")), _float(_first(e, "20"))
            r = abs(_float(_first(e, "40")))
            points.extend([(x-r, y-r), (x+r, y+r)])
            shapes.append(f'<circle cx="{x}" cy="{-y}" r="{r}" />')
        elif t in {"LWPOLYLINE", "POLYLINE"}:
            xs = [_float(v) for v in _values(e, "10")]
            ys = [_float(v) for v in _values(e, "20")]
            pts = list(zip(xs, ys))
            if len(pts) >= 2:
                points.extend(pts)
                attr = " ".join(f"{x},{-y}" for x, y in pts)
                shapes.append(f'<polyline points="{attr}" />')
        elif t == "ARC":
            x, y = _float(_first(e, "10")), _float(_first(e, "20"))
            r = abs(_float(_first(e, "40")))
            a1 = math.radians(_float(_first(e, "50")))
            a2 = math.radians(_float(_first(e, "51")))
            sx, sy = x + r * math.cos(a1), y + r * math.sin(a1)
            ex, ey = x + r * math.cos(a2), y + r * math.sin(a2)
            large = 1 if abs((a2 - a1) % (2 * math.pi)) > math.pi else 0
            points.extend([(x-r, y-r), (x+r, y+r)])
            shapes.append(f'<path d="M {sx} {-sy} A {r} {r} 0 {large} 0 {ex} {-ey}" />')

    minx, miny, maxx, maxy = _bounds(points)
    # Convert DXF Y-up into SVG coordinates already using negative values.
    view_minx = minx
    view_miny = -maxy
    width = maxx - minx
    height = maxy - miny
    pad = max(width, height) * 0.08 + 10
    viewbox = f"{view_minx-pad} {view_miny-pad} {width+2*pad} {height+2*pad}"

    body = "\n".join(shapes) or '<text x="0" y="0" font-size="12">No supported DXF entities found</text>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" role="img" aria-label="{html.escape(title)}">
  <rect x="{view_minx-pad}" y="{view_miny-pad}" width="{width+2*pad}" height="{height+2*pad}" fill="white"/>
  <g fill="none" stroke="#111827" stroke-width="1.2" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round">
    {body}
  </g>
</svg>"""
