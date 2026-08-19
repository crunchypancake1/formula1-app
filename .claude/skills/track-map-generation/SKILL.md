---
name: track-map-generation
description: >
  Use when asked to generate track layout SVG maps, regenerate circuit visuals,
  add new tracks, or update track-layouts in public/images/track-layouts/.
  Also use when a new F1 circuit is added to the game and needs a map generated.
---

# Track Map Generation

Generate track layout SVGs using FastF1's MultiViewer API. Each SVG renders marshal zone segments as separate `<path>` elements with corner markers and a start/finish line.

## Prerequisites

- Python 3.12+ with `numpy` and `fastf1` installed
- Internet access (fetches circuit geometry from MultiViewer API)
- No database dependency

## Quick Start

```bash
# Generate all tracks
python .claude/skills/track-map-generation/generate_track_svgs.py

# Single track only
python .claude/skills/track-map-generation/generate_track_svgs.py --track 11

# Custom output directory
python .claude/skills/track-map-generation/generate_track_svgs.py --output-dir /tmp/svgs

# Different season year (affects circuit layout data)
python .claude/skills/track-map-generation/generate_track_svgs.py --year 2025
```

Default output: `code/web/public/images/track-layouts/`

## Track Registry

The script maps F1 game `track_id` values to FastF1 MultiViewer `circuit_key` values. To add a new track:

1. Find the game's `track_id` (from UDP spec or `telemetry.tracks` table)
2. Find the FastF1 `circuit_key` (from MultiViewer API)
3. Get the track length in meters (from game telemetry data)
4. Add entries to both `_TRACKS` and `_TRACK_NAMES` dicts in the script
5. Run the script with `--track <id>` to generate the SVG

## SVG Structure

Each generated SVG contains:
- **Marshal zone paths**: One `<path class="zone">` per marshal zone with `data-zone`, `data-start`, `data-end` attributes (fractional track position)
- **Corner markers**: `<circle>` + `<text>` for each numbered corner (e.g., "1", "2a", "2b")
- **Start/finish line**: Perpendicular `<line>` at polyline index 0
- **Styling**: Uses `currentColor` so SVGs inherit the parent's text color (works in both light and dark themes)

Canvas: 800x600 with 40px padding. All coordinates auto-scaled to fit.

## How It Works

1. Fetches circuit polyline (x/y coordinates), marshal sectors, and corner data from FastF1's MultiViewer API
2. Applies rotation (if specified in API response) around the centroid
3. Computes cumulative arc-length distances along the polyline
4. Maps marshal sector boundaries to polyline indices (handles wrap-around at start/finish)
5. Builds SVG path `d` attributes from polyline slices
6. Fits everything to the 800x600 viewport with Y-axis flip

## Common Mistakes

- **Wrong circuit_key**: The MultiViewer circuit_key is NOT the same as the game's track_id. Cross-reference carefully.
- **Missing track in `_TRACK_NAMES`**: The script skips tracks without a filename mapping even if they're in `_TRACKS`.
- **Year matters**: Circuit layouts can change between seasons. Use `--year` matching the game version.
