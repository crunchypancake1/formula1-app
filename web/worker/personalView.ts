/**
 * The personal driver view's HTML shell (`/me`). Same pattern as
 * `dashboard.ts`: a static shell that polls `/api/me` and renders
 * client-side — no server-rendered state beyond the shell itself.
 */
export function renderPersonalView(): string {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>F1 My Race</title>
<style>${STYLES}</style>
</head>
<body>
<div id="app">
  <div class="boot">Connecting&hellip;</div>
</div>
<script>${SCRIPT}</script>
</body>
</html>`;
}

const STYLES = `
:root {
  color-scheme: dark;
  --bg: #0a0a0d;
  --panel: #16161c;
  --border: #2a2a34;
  --text: #eaeaef;
  --text-dim: #9494a3;
  --accent: #e10600;
  --green: #2ecc71;
  --yellow: #f5c518;
  --blue: #3b82f6;

  --mercedes: #27f4d2; --ferrari: #e8002d; --red-bull-racing: #3671c6;
  --williams: #64c4ff; --aston-martin: #229971; --alpine: #0093cc;
  --rb: #6692ff; --haas: #b6babd; --mclaren: #ff8000; --sauber: #52e252;
  --audi: #bb0a30; --cadillac: #8a8f98; --team-fallback: #7a7a86;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}

.boot, .empty {
  display: grid;
  place-items: center;
  min-height: 100vh;
  text-align: center;
  padding: 2rem;
  color: var(--text-dim);
}
.empty h1 { color: var(--text); font-size: 1.4rem; margin: 0 0 0.5rem; }
.empty p { max-width: 32rem; margin: 0 0 1rem; }
.empty a { color: var(--blue); }

.view { max-width: 720px; margin: 0 auto; padding: 1rem clamp(0.75rem, 2vw, 2rem) 3rem; }

.back-link { display: inline-block; color: var(--text-dim); font-size: 0.85rem; text-decoration: none; margin-bottom: 1rem; }
.back-link:hover { color: var(--text); }

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
}
.panel h2 {
  font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--text-dim); margin: 0 0 0.75rem;
}

.identity { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem; }
.identity-left { display: flex; align-items: center; gap: 0.75rem; }
.identity-left .team-bar { width: 5px; height: 2.2rem; border-radius: 3px; }
.identity-name { font-size: 1.3rem; font-weight: 700; }
.identity-sub { color: var(--text-dim); font-size: 0.85rem; }
.identity-stats { display: flex; gap: 1.5rem; }
.identity-stats .stat { text-align: right; }
.identity-stats .value { font-size: 1.2rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.identity-stats .label { font-size: 0.65rem; color: var(--text-dim); letter-spacing: 0.06em; text-transform: uppercase; }

.battle { display: flex; flex-direction: column; gap: 0.5rem; }
.battle-row {
  display: flex; align-items: center; gap: 0.6rem;
  padding: 0.6rem 0.75rem; border-radius: 8px; border: 1px solid var(--border);
}
.battle-row.you { border-color: var(--accent); background: rgba(225,6,0,0.08); }
.battle-row.close { border-color: var(--yellow); }
.battle-row .team-bar { width: 4px; height: 1.6rem; border-radius: 2px; }
.battle-name { font-weight: 600; flex: 1; }
.battle-gap { font-variant-numeric: tabular-nums; color: var(--text-dim); width: 4.5rem; text-align: right; }
.battle-tyre {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.4rem; height: 1.4rem; border-radius: 50%; font-size: 0.62rem; font-weight: 800;
  border: 2px solid currentColor;
}
.tyre.soft { color: #e8002d; } .tyre.medium { color: #f5c518; } .tyre.hard { color: #d8d8d8; }
.tyre.inter { color: #2ecc71; } .tyre.wet { color: #3b82f6; } .tyre.unknown { color: #7a7a86; }
.badge { font-size: 0.62rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 3px; letter-spacing: 0.04em; }
.badge.drs { background: rgba(46,204,113,0.18); color: var(--green); }

table.tyres { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
table.tyres th {
  text-align: left; font-size: 0.65rem; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--text-dim); padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--border);
}
table.tyres td { padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border); }
table.tyres tr:last-child td { border-bottom: none; }
table.tyres tr.fitted td:first-child { font-weight: 700; }

.wear-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }
.wear-cell { display: flex; justify-content: space-between; padding: 0.4rem 0.6rem; background: var(--bg); border-radius: 6px; }
.wear-cell .label { color: var(--text-dim); font-size: 0.8rem; }
.wear-cell .value { font-variant-numeric: tabular-nums; font-weight: 600; }

.withheld { color: var(--text-dim); font-size: 0.85rem; }
.withheld .hint { display: block; margin-top: 0.25rem; font-size: 0.78rem; }
.waiting { color: var(--text-dim); font-size: 0.85rem; }
`;

const SCRIPT = `
(function () {
  var POLL_MS = 3000;
  var app = document.getElementById("app");

  var TEAM_COLOR_VARS = {
    MERCEDES: "--mercedes", FERRARI: "--ferrari", RED_BULL_RACING: "--red-bull-racing",
    WILLIAMS: "--williams", ASTON_MARTIN: "--aston-martin", ALPINE: "--alpine",
    RB: "--rb", HAAS: "--haas", MCLAREN: "--mclaren", SAUBER: "--sauber",
    AUDI: "--audi", CADILLAC: "--cadillac"
  };

  function teamColor(teamName) {
    var base = String(teamName || "").replace(/_\\d+$/, "");
    var v = TEAM_COLOR_VARS[base];
    return v ? "var(" + v + ")" : "var(--team-fallback)";
  }

  function parseMs(v) {
    if (v === null || v === undefined) return null;
    var n = typeof v === "number" ? v : Number(v);
    return isFinite(n) ? n : null;
  }

  function formatGap(ms) {
    var n = parseMs(ms);
    if (n === null) return "—";
    return "+" + (n / 1000).toFixed(3);
  }

  function formatClock(totalSeconds) {
    if (totalSeconds === null || totalSeconds === undefined) return "—";
    var s = Math.max(0, Math.round(totalSeconds));
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = s % 60;
    return h > 0
      ? h + ":" + String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0")
      : m + ":" + String(sec).padStart(2, "0");
  }

  function tyreClass(visual) {
    switch (visual) {
      case "SOFT": return "soft";
      case "MEDIUM": return "medium";
      case "HARD": return "hard";
      case "INTER": return "inter";
      case "WET": return "wet";
      default: return "unknown";
    }
  }

  function tyreLetter(visual) {
    switch (visual) {
      case "SOFT": return "S";
      case "MEDIUM": return "M";
      case "HARD": return "H";
      case "INTER": return "I";
      case "WET": return "W";
      default: return "?";
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function notLive() {
    return '<div class="empty"><h1>No Live Session</h1>' +
      '<p>Nothing is currently being tracked.</p>' +
      '<a href="/">Back to dashboard</a></div>';
  }

  function noDriver() {
    return '<div class="empty"><h1>Not Sure Which Car Is Yours</h1>' +
      '<p>We could not confidently match your Discord account to a driver in this session.</p>' +
      '<a href="/">Back to dashboard</a></div>';
  }

  function renderIdentity(data) {
    var f = data.frame, s = data.session, tl = data.timeline;
    var totalLaps = (tl && tl.total_laps) || (s && s.total_laps);
    var stats = "";
    if (totalLaps) {
      stats += '<div class="stat"><div class="value">' + (f.current_lap_num != null ? f.current_lap_num : "—") +
        " / " + totalLaps + '</div><div class="label">Lap</div></div>';
    }
    if (tl && tl.session_time_left != null) {
      stats += '<div class="stat"><div class="value">' + formatClock(tl.session_time_left) + '</div><div class="label">Remaining</div></div>';
    }
    return '<div class="panel identity">' +
      '<div class="identity-left"><span class="team-bar" style="background:' + teamColor(f.team_name) + '"></span>' +
      '<div><div class="identity-name">P' + (f.position != null ? f.position : "—") + ' · ' + escapeHtml(f.driver_name) +
      ' #' + f.race_number + '</div><div class="identity-sub">' + escapeHtml(f.team_display_name) + '</div></div></div>' +
      '<div class="identity-stats">' + stats + '</div>' +
      '<a class="back-link" href="/">← Dashboard</a>' +
    '</div>';
  }

  function battleRow(label, name, team, tyre, age, gap, isClose, isYou) {
    var cls = "battle-row" + (isYou ? " you" : "") + (isClose ? " close" : "");
    var badges = "";
    return '<div class="' + cls + '">' +
      '<span class="team-bar" style="background:' + teamColor(team) + '"></span>' +
      '<span class="battle-name">' + (name ? escapeHtml(name) : "—") + '</span>' +
      (tyre ? '<span class="battle-tyre tyre ' + tyreClass(tyre) + '">' + tyreLetter(tyre) + '</span>' : "") +
      '<span class="mono" style="width:2rem;text-align:right;">' + (age != null ? age : "—") + '</span>' +
      badges +
      '<span class="battle-gap">' + gap + '</span>' +
    '</div>';
  }

  function renderBattle(f) {
    var aheadGap = formatGap(f.gap_to_car_ahead_ms);
    var behindGap = formatGap(f.gap_to_car_behind_ms);
    var aheadClose = parseMs(f.gap_to_car_ahead_ms) !== null && parseMs(f.gap_to_car_ahead_ms) < 1000;
    var behindClose = parseMs(f.gap_to_car_behind_ms) !== null && parseMs(f.gap_to_car_behind_ms) < 1000;

    var rows = "";
    if (f.ahead_driver_name) {
      rows += battleRow("ahead", f.ahead_driver_name, f.ahead_team_name, f.ahead_visual_tyre_compound, f.ahead_tyres_age_laps, aheadGap, aheadClose, false);
    }
    var youBadges = "";
    if (f.overtake_available) youBadges += '<span class="badge drs">' + (f.overtake_active ? "BOOST ACTIVE" : "BOOST READY") + '</span>';
    rows += '<div class="battle-row you">' +
      '<span class="team-bar" style="background:' + teamColor(f.team_name) + '"></span>' +
      '<span class="battle-name">' + escapeHtml(f.driver_name) + ' (you)</span>' +
      (f.visual_tyre_compound ? '<span class="battle-tyre tyre ' + tyreClass(f.visual_tyre_compound) + '">' + tyreLetter(f.visual_tyre_compound) + '</span>' : "") +
      '<span class="mono" style="width:2rem;text-align:right;">' + (f.tyres_age_laps != null ? f.tyres_age_laps : "—") + '</span>' +
      youBadges +
      '<span class="battle-gap"></span>' +
    '</div>';
    if (f.behind_driver_name) {
      rows += battleRow("behind", f.behind_driver_name, f.behind_team_name, f.behind_visual_tyre_compound, f.behind_tyres_age_laps, behindGap, behindClose, false);
    }

    return '<div class="panel"><h2>Battle</h2><div class="battle">' + rows + '</div></div>';
  }

  function renderTyreSets(data) {
    if (!data.telemetryPublic) {
      return '<div class="panel"><h2>Available Tyre Sets</h2><div class="withheld">' +
        'Your Telemetry is set to Restricted, so the game doesn\\'t share tyre-set data.' +
        '<span class="hint">Switch it to Public in the game\\'s telemetry settings to turn this panel on.</span></div></div>';
    }
    if (!data.tyreSets || !data.tyreSets.length) {
      return '<div class="panel"><h2>Available Tyre Sets</h2><div class="waiting">Waiting for data…</div></div>';
    }
    var rows = data.tyreSets.map(function (t) {
      return '<tr class="' + (t.fitted ? "fitted" : "") + '">' +
        '<td><span class="tyre ' + tyreClass(t.visual_compound) + '">' + tyreLetter(t.visual_compound) + '</span></td>' +
        '<td class="mono">' + t.wear + '%</td>' +
        '<td class="mono">' + (t.usable_life - t.wear) + ' laps</td>' +
        '<td class="mono">' + (t.lap_delta_time_ms > 0 ? "+" : "") + (t.lap_delta_time_ms / 1000).toFixed(2) + 's</td>' +
        '<td>' + (t.fitted ? "Fitted" : "") + '</td>' +
      '</tr>';
    }).join("");
    return '<div class="panel"><h2>Available Tyre Sets (lap ' + data.tyreSets[0].lap_number + ')</h2>' +
      '<table class="tyres"><thead><tr><th>Tyre</th><th>Wear</th><th>Life Left</th><th>Delta</th><th></th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>';
  }

  function renderTyresNow(data) {
    if (!data.telemetryPublic) {
      return '<div class="panel"><h2>Tyres Now</h2><div class="withheld">' +
        'Your Telemetry is set to Restricted, so the game doesn\\'t share wear data.' +
        '<span class="hint">Switch it to Public in the game\\'s telemetry settings to turn this panel on.</span></div></div>';
    }
    if (!data.damage) {
      return '<div class="panel"><h2>Tyres Now</h2><div class="waiting">Waiting for data…</div></div>';
    }
    var d = data.damage;
    function cell(label, v) {
      return '<div class="wear-cell"><span class="label">' + label + '</span><span class="value">' +
        (v != null ? v.toFixed(1) + "%" : "—") + '</span></div>';
    }
    return '<div class="panel"><h2>Tyres Now</h2><div class="wear-grid">' +
      cell("Front Left", d.tyres_wear_fl) + cell("Front Right", d.tyres_wear_fr) +
      cell("Rear Left", d.tyres_wear_rl) + cell("Rear Right", d.tyres_wear_rr) +
    '</div></div>';
  }

  function render(data) {
    if (!data.live) {
      app.innerHTML = notLive();
      return;
    }
    if (!data.frame) {
      app.innerHTML = noDriver();
      return;
    }

    app.innerHTML = '<div class="view">' +
      renderIdentity(data) +
      renderBattle(data.frame) +
      renderTyreSets(data) +
      renderTyresNow(data) +
    '</div>';
  }

  function poll() {
    fetch("/api/me")
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () { app.innerHTML = notLive(); })
      .then(function () { setTimeout(poll, POLL_MS); });
  }

  poll();
})();
`;
