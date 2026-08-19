#!/usr/bin/env python3
"""Generate track layout SVGs with one <path> per marshal zone.

Uses FastF1 MultiViewer API only — no database dependency.

Usage:
    python code/api/scripts/generate_track_svgs.py
    python code/api/scripts/generate_track_svgs.py --track 11  # Monza only
    python code/api/scripts/generate_track_svgs.py --output-dir /tmp/svgs
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

# ---------------------------------------------------------------------------
# Track registry: game track_id -> (MultiViewer circuit_key, track_length_m)
# ---------------------------------------------------------------------------

_TRACKS: dict[int, tuple[int, int]] = {
    0:  (10, 5278),
    2:  (49, 5451),
    3:  (63, 5412),
    4:  (15, 4657),
    5:  (22, 3337),
    6:  (23, 4361),
    7:  (2, 5891),
    9:  (4, 4381),
    10: (7, 7004),
    11: (39, 5793),
    12: (61, 4940),
    13: (46, 5807),
    14: (70, 5281),
    15: (9, 5513),
    16: (14, 4309),
    17: (19, 4318),
    19: (65, 4304),
    20: (144, 6003),
    26: (55, 4259),
    27: (6, 4909),
    29: (149, 6174),
    30: (151, 5412),
    31: (152, 6201),
    32: (150, 5419),
}

_TRACK_NAMES: dict[int, str] = {
    0:  "melbourne",
    2:  "shanghai",
    3:  "bahrain",
    4:  "catalunya",
    5:  "monaco",
    6:  "montreal",
    7:  "silverstone",
    9:  "hungaroring",
    10: "spa",
    11: "monza",
    12: "singapore",
    13: "suzuka",
    14: "abu-dhabi",
    15: "texas",
    16: "brazil",
    17: "austria",
    19: "mexico",
    20: "baku",
    26: "zandvoort",
    27: "imola",
    29: "jeddah",
    30: "miami",
    31: "las-vegas",
    32: "losail",
}

# SVG canvas dimensions
SVG_WIDTH = 800
SVG_HEIGHT = 600
SVG_PADDING = 40


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _cumulative_distances(
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Compute cumulative arc-length distances along the polyline."""
    dx = np.diff(x)
    dy = np.diff(y)
    seg_lengths = np.sqrt(dx ** 2 + dy ** 2)
    cum = np.zeros(len(x), dtype=np.float64)
    cum[1:] = np.cumsum(seg_lengths)
    return cum


def _rotate_points(
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
    angle_deg: float,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Rotate points around their centroid by angle_deg degrees."""
    cx = float(np.mean(x))
    cy = float(np.mean(y))
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rx = cx + (x - cx) * cos_a - (y - cy) * sin_a
    ry = cy + (x - cx) * sin_a + (y - cy) * cos_a
    return rx, ry


def _fit_to_viewport(
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
    width: int,
    height: int,
    padding: int,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Scale and translate points to fit within SVG viewport, flipping Y axis."""
    x_min, x_max = float(np.min(x)), float(np.max(x))
    y_min, y_max = float(np.min(y)), float(np.max(y))

    x_range = x_max - x_min
    y_range = y_max - y_min

    if x_range == 0 or y_range == 0:
        return x, y

    usable_w = width - 2 * padding
    usable_h = height - 2 * padding

    scale = min(usable_w / x_range, usable_h / y_range)

    sx = (x - x_min) * scale + padding + (usable_w - x_range * scale) / 2
    # Flip Y: SVG Y increases downward, polyline Y typically increases upward
    sy = height - padding - (y - y_min) * scale - (usable_h - y_range * scale) / 2

    return sx, sy


def _polyline_index_at(
    cum: npt.NDArray[np.float64],
    target: float,
) -> int:
    """Return the polyline index closest to the target cumulative distance."""
    idx = int(np.searchsorted(cum, target))
    return min(idx, len(cum) - 1)


def _perp_offset(
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
    idx: int,
    half_width: float,
) -> tuple[float, float, float, float]:
    """Compute perpendicular endpoints for a cross-track line at index idx."""
    n = len(x)
    if n < 2:
        return float(x[idx]), float(y[idx]) - half_width, float(x[idx]), float(y[idx]) + half_width

    if idx == 0:
        dx = float(x[1] - x[0])
        dy = float(y[1] - y[0])
    elif idx == n - 1:
        dx = float(x[-1] - x[-2])
        dy = float(y[-1] - y[-2])
    else:
        dx = float(x[idx + 1] - x[idx - 1])
        dy = float(y[idx + 1] - y[idx - 1])

    length = math.sqrt(dx ** 2 + dy ** 2)
    if length == 0:
        nx, ny = 0.0, half_width
    else:
        # Perpendicular: rotate 90°
        nx = -dy / length * half_width
        ny = dx / length * half_width

    px, py = float(x[idx]), float(y[idx])
    return px - nx, py - ny, px + nx, py + ny


# ---------------------------------------------------------------------------
# SVG path builder
# ---------------------------------------------------------------------------

def _path_from_indices(
    sx: npt.NDArray[np.float64],
    sy: npt.NDArray[np.float64],
    i_start: int,
    i_end: int,
) -> str:
    """Build an SVG path 'd' attribute from a slice of the polyline."""
    if i_start >= i_end:
        return ""

    parts: list[str] = []
    parts.append(f"M{sx[i_start]:.1f},{sy[i_start]:.1f}")
    for i in range(i_start + 1, i_end + 1):
        parts.append(f"L{sx[i]:.1f},{sy[i]:.1f}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# SVG template
# ---------------------------------------------------------------------------

_SVG_STYLE = """\
    .zone { stroke: currentColor; fill: none; stroke-width: 10; stroke-linejoin: round; stroke-linecap: round; opacity: 0.85; }
    .corner-dot { fill: currentColor; stroke: none; }
    .corner-num { fill: currentColor; font-size: 12px; font-weight: bold; font-family: Arial, sans-serif; }
    .sf-line { stroke: currentColor; stroke-width: 3; }"""


def _build_svg(
    sx: npt.NDArray[np.float64],
    sy: npt.NDArray[np.float64],
    zone_segments: list[dict[str, Any]],
    corners: list[dict[str, Any]],
) -> str:
    """Assemble the final SVG string."""
    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}"'
        f' viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">'
    )
    lines.append("  <style>")
    lines.append(_SVG_STYLE)
    lines.append("  </style>")
    lines.append("")

    # Zone paths
    for seg in zone_segments:
        lines.append(
            f'  <path d="{seg["d"]}" class="zone"'
            f' data-zone="{seg["zone_idx"]}"'
            f' data-start="{seg["frac_start"]:.3f}"'
            f' data-end="{seg["frac_end"]:.3f}"/>'
        )
    lines.append("")

    # Start/finish line at the first polyline point (index 0)
    x1, y1, x2, y2 = _perp_offset(sx, sy, 0, 9.0)
    lines.append(
        f'  <!-- Start/Finish line -->'
        f'\n  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="sf-line"/>'
    )
    lines.append("")

    # Corner markers
    lines.append("  <!-- Corner markers -->")
    for c in corners:
        cx = c["cx"]
        cy = c["cy"]
        num = c["number"]
        letter = c.get("letter", "")
        label = f"{num}{letter}"
        # Offset text label outward from track centroid
        lines.append(f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" class="corner-dot"/>')
        lines.append(
            f'  <text x="{cx:.1f}" y="{cy - 8:.1f}" text-anchor="middle" class="corner-num">{label}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core generation logic
# ---------------------------------------------------------------------------

def _sort_marshal_sectors(
    sectors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort marshal sectors into track order.

    The API returns sectors where `length` is the cumulative polyline distance
    at which each sector STARTS. Sectors with very large length values near the
    end of the track represent sectors that wrap around; they must be sorted
    correctly into the sector sequence.

    Strategy: sort by `length` ascending. The sector that spans the
    start/finish line will have a `length` near polyline_total (its start is
    near the end of the polyline, and it wraps to index 0).
    """
    return sorted(sectors, key=lambda s: float(s["length"]))


def generate_svg_for_track(
    track_id: int,
    output_dir: Path,
    year: int = 2024,
) -> None:
    """Fetch data and write SVG for a single track."""
    import fastf1.mvapi.api as mvapi  # type: ignore[import-untyped]

    track_name = _TRACK_NAMES.get(track_id)
    if not track_name:
        print(f"  [skip] No SVG filename mapping for track_id={track_id}")
        return

    circuit_key, _ = _TRACKS[track_id]
    print(f"  Fetching circuit_key={circuit_key} ({track_name})...")

    raw_data = mvapi.get_circuit(year=year, circuit_key=circuit_key)
    if not raw_data:
        print(f"  [error] No data returned for circuit_key={circuit_key}")
        return

    data: dict[str, Any] = dict(raw_data)
    raw_x: list[float] = data.get("x", [])
    raw_y: list[float] = data.get("y", [])
    if len(raw_x) < 3 or len(raw_y) < 3:
        print(f"  [error] Insufficient polyline data for {track_name}")
        return

    x = np.array(raw_x, dtype=np.float64)
    y = np.array(raw_y, dtype=np.float64)

    rotation: float = float(data.get("rotation", 0.0))
    if rotation != 0.0:
        x, y = _rotate_points(x, y, rotation)

    cum = _cumulative_distances(x, y)
    polyline_total = float(cum[-1])
    if polyline_total <= 0:
        print(f"  [error] Zero-length polyline for {track_name}")
        return

    # Fit to SVG viewport
    sx, sy = _fit_to_viewport(x, y, SVG_WIDTH, SVG_HEIGHT, SVG_PADDING)

    # Recompute cumulative distances on original (unscaled) coords for fraction calc
    # (scale doesn't change fractions, but we already have cum)

    # Marshal sectors
    raw_sectors: list[dict[str, Any]] = data.get("marshalSectors", [])
    if not raw_sectors:
        print(f"  [error] No marshalSectors for {track_name}")
        return

    sorted_sectors = _sort_marshal_sectors(raw_sectors)
    n_sectors = len(sorted_sectors)

    zone_segments: list[dict[str, Any]] = []

    for i, sector in enumerate(sorted_sectors):
        start_dist = float(sector["length"])

        # End distance is the start of the next sector; last sector wraps to first
        if i + 1 < n_sectors:
            end_dist = float(sorted_sectors[i + 1]["length"])
        else:
            # Last sector wraps around: ends at the first sector's start
            end_dist = float(sorted_sectors[0]["length"])

        frac_start = start_dist / polyline_total
        frac_end = end_dist / polyline_total

        # Handle wrap-around: segment crosses start/finish line
        if end_dist <= start_dist:
            # Two sub-segments: start_dist -> end of polyline, then 0 -> end_dist
            i_s1 = _polyline_index_at(cum, start_dist)
            i_e1 = len(cum) - 1
            d1 = _path_from_indices(sx, sy, i_s1, i_e1)

            i_s2 = 0
            i_e2 = _polyline_index_at(cum, end_dist)
            d2 = _path_from_indices(sx, sy, i_s2, i_e2)

            d = (d1 + " " + d2).strip()
        else:
            i_start = _polyline_index_at(cum, start_dist)
            i_end = _polyline_index_at(cum, end_dist)
            d = _path_from_indices(sx, sy, i_start, i_end)

        if not d:
            continue

        zone_segments.append({
            "zone_idx": i,
            "d": d,
            "frac_start": frac_start,
            "frac_end": frac_end,
        })

    # Corner markers
    raw_corners: list[dict[str, Any]] = data.get("corners", [])
    corner_markers: list[dict[str, Any]] = []

    for corner in raw_corners:
        corner_dist = float(corner["length"])
        idx = _polyline_index_at(cum, corner_dist)
        corner_markers.append({
            "number": int(corner["number"]),
            "letter": str(corner.get("letter", "") or ""),
            "cx": float(sx[idx]),
            "cy": float(sy[idx]),
        })

    svg_content = _build_svg(sx, sy, zone_segments, corner_markers)

    out_path = output_dir / f"{track_name}.svg"
    out_path.write_text(svg_content, encoding="utf-8")
    print(f"  [ok] Written {out_path} ({n_sectors} zones, {len(corner_markers)} corners)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate track layout SVGs using FastF1 marshal zone data."
    )
    parser.add_argument(
        "--track",
        type=int,
        default=None,
        metavar="TRACK_ID",
        help="Regenerate only this track_id (default: all tracks)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[4]
        / "code" / "web" / "public" / "images" / "track-layouts",
        metavar="DIR",
        help="Output directory for SVG files",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        metavar="YEAR",
        help="F1 season year for MultiViewer API (default: 2024)",
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    track_ids = [args.track] if args.track is not None else sorted(_TRACKS.keys())

    failed: list[int] = []
    for track_id in track_ids:
        if track_id not in _TRACKS:
            print(f"[warn] track_id={track_id} not in registry, skipping")
            continue
        print(f"Track {track_id} ({_TRACK_NAMES.get(track_id, '?')}):")
        try:
            generate_svg_for_track(track_id, output_dir, year=args.year)
        except Exception as exc:
            print(f"  [error] {exc}")
            failed.append(track_id)

    print()
    print(f"Done. {len(track_ids) - len(failed)}/{len(track_ids)} tracks succeeded.")
    if failed:
        print(f"Failed track IDs: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
