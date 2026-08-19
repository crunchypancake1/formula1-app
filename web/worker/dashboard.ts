/**
 * The live dashboard's HTML shell. Everything renders client-side from
 * `/api/live`, polled on an interval — there is no server-rendered state here
 * beyond the static shell, which keeps this a plain Hono route (see
 * `worker/index.ts`) rather than needing a frontend build step.
 */
export function renderDashboard(): string {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>F1 Live Dashboard</title>
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
  --panel-alt: #1d1d25;
  --border: #2a2a34;
  --text: #eaeaef;
  --text-dim: #9494a3;
  --accent: #e10600;
  --purple: #b833ff;
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

.boot {
  display: grid;
  place-items: center;
  min-height: 100vh;
  color: var(--text-dim);
  font-size: 1.1rem;
}

#app { min-height: 100vh; }

/* ---- empty state ---- */
.empty {
  display: grid;
  place-items: center;
  min-height: 100vh;
  text-align: center;
  padding: 2rem;
}
.empty svg { width: 56px; height: 56px; color: var(--text-dim); margin-bottom: 1rem; }
.empty h1 { font-size: 1.4rem; margin: 0 0 0.5rem; }
.empty p { color: var(--text-dim); max-width: 32rem; margin: 0; }

/* ---- layout ---- */
.dashboard { max-width: 1400px; margin: 0 auto; padding: 1rem clamp(0.75rem, 2vw, 2rem) 3rem; }

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 1rem 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1rem;
}
.header-left { display: flex; align-items: center; gap: 0.9rem; }
.live-badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: var(--accent); color: #fff;
  font-weight: 700; font-size: 0.72rem; letter-spacing: 0.06em;
  padding: 0.28rem 0.6rem; border-radius: 4px;
}
.live-badge .dot { width: 7px; height: 7px; border-radius: 50%; background: #fff; animation: pulse 1.4s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
.session-type { font-size: 1.3rem; font-weight: 700; }
.track-line { color: var(--text-dim); font-size: 0.9rem; }

.header-right { display: flex; gap: 1.75rem; align-items: center; flex-wrap: wrap; }
.stat { text-align: right; }
.stat .value { font-size: 1.3rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat .label { font-size: 0.68rem; color: var(--text-dim); letter-spacing: 0.06em; text-transform: uppercase; }

.status-strip { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1rem; }
.pill {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: var(--panel); border: 1px solid var(--border);
  padding: 0.35rem 0.7rem; border-radius: 999px; font-size: 0.8rem; color: var(--text-dim);
}
.pill.warn { border-color: var(--yellow); color: var(--yellow); }
.pill.danger { border-color: var(--accent); color: var(--accent); background: rgba(225,6,0,0.08); }
.pill.safety { border-color: var(--yellow); color: var(--yellow); }

.grid {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(420px, 1.4fr);
  gap: 1rem;
}
@media (max-width: 980px) { .grid { grid-template-columns: 1fr; } }

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem;
}
.panel h2 {
  font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--text-dim); margin: 0 0 0.75rem;
}

/* ---- track map ---- */
.track-map-wrap { position: relative; aspect-ratio: 4 / 3; }
.track-map-wrap svg.layout { width: 100%; height: 100%; color: #3a3a46; }
.track-map-wrap .zone { color: #3a3a46; }
.track-map-wrap .corner-num, .track-map-wrap .corner-dot { fill: #4b4b5a; }
.car-dot {
  position: absolute; width: 15px; height: 15px; border-radius: 50%;
  border: 2px solid #0a0a0d; transform: translate(-50%, -50%);
  display: grid; place-items: center;
  font-size: 8px; font-weight: 800; color: #0a0a0d;
  transition: left 0.9s linear, top 0.9s linear;
  z-index: 2;
}
.car-dot.player-focus { box-shadow: 0 0 0 2px #fff; }
.no-map { display: grid; place-items: center; height: 100%; color: var(--text-dim); font-size: 0.85rem; text-align: center; }

/* ---- leaderboard ---- */
table.board { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
table.board th {
  text-align: left; font-size: 0.68rem; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--text-dim); padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border);
}
table.board td { padding: 0.45rem 0.5rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
table.board tr:last-child td { border-bottom: none; }
table.board tr.retired td { opacity: 0.45; }
.pos { font-weight: 800; font-variant-numeric: tabular-nums; width: 1.6rem; }
.team-bar { display: inline-block; width: 4px; height: 1.4rem; border-radius: 2px; margin-right: 0.55rem; vertical-align: middle; }
.driver-name { font-weight: 600; }
.driver-cell { display: flex; align-items: center; }
.num-tag { color: var(--text-dim); font-size: 0.72rem; margin-left: 0.4rem; }
.mono { font-variant-numeric: tabular-nums; }
.lap-time.session-fastest { color: var(--purple); font-weight: 700; }
.lap-time.personal-best { color: var(--green); font-weight: 700; }
.tyre {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.4rem; height: 1.4rem; border-radius: 50%; font-size: 0.62rem; font-weight: 800;
  border: 2px solid currentColor;
}
.tyre.soft { color: #e8002d; } .tyre.medium { color: #f5c518; } .tyre.hard { color: #d8d8d8; }
.tyre.inter { color: #2ecc71; } .tyre.wet { color: #3b82f6; } .tyre.unknown { color: #7a7a86; }
.badge { font-size: 0.66rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 3px; letter-spacing: 0.04em; }
.badge.pit { background: rgba(59,130,246,0.18); color: var(--blue); }
.badge.boost { background: rgba(46,204,113,0.18); color: var(--green); }
.badge.out { background: rgba(148,148,163,0.18); color: var(--text-dim); }
.cutoff-row td { padding: 0.15rem 0.5rem; border-bottom: 1px dashed var(--accent); position: relative; }
.cutoff-label {
  font-size: 0.62rem; letter-spacing: 0.06em; color: var(--accent); font-weight: 700;
  text-align: center; display: block; padding-top: 0.15rem;
}

/* ---- feed ---- */
.feed { grid-column: 1 / -1; }
.feed-list { list-style: none; margin: 0; padding: 0; max-height: 360px; overflow-y: auto; }
.feed-list li {
  display: flex; gap: 0.6rem; align-items: baseline;
  padding: 0.5rem 0.25rem; border-bottom: 1px solid var(--border); font-size: 0.85rem;
}
.feed-list li:last-child { border-bottom: none; }
.feed-time { color: var(--text-dim); font-variant-numeric: tabular-nums; font-size: 0.75rem; width: 3.4rem; flex: none; }
.feed-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; margin-top: 0.35rem; }
.feed-dot.flag { background: var(--text-dim); }
.feed-dot.lights { background: var(--yellow); }
.feed-dot.drs { background: var(--green); }
.feed-dot.safety-car { background: var(--yellow); }
.feed-dot.penalty { background: var(--accent); }
.feed-dot.retirement { background: var(--text-dim); }
.feed-dot.fastest-lap { background: var(--purple); }
.feed-empty { color: var(--text-dim); font-size: 0.85rem; padding: 0.5rem 0.25rem; }
`;

const SCRIPT = `
(function () {
  var POLL_MS = 3000;
  var app = document.getElementById("app");
  var svgCache = {};

  var TEAM_COLOR_VARS = {
    MERCEDES: "--mercedes", FERRARI: "--ferrari", RED_BULL_RACING: "--red-bull-racing",
    WILLIAMS: "--williams", ASTON_MARTIN: "--aston-martin", ALPINE: "--alpine",
    RB: "--rb", HAAS: "--haas", MCLAREN: "--mclaren", SAUBER: "--sauber",
    AUDI: "--audi", CADILLAC: "--cadillac"
  };

  var TRACK_SLUGS = {
    MELBOURNE: "melbourne", SHANGHAI: "shanghai", SAKHIR_BAHRAIN: "sakhir-bahrain",
    CATALUNYA: "catalunya", MONACO: "monaco", MONTREAL: "montreal",
    SILVERSTONE: "silverstone", SILVERSTONE_REVERSE: "silverstone",
    HUNGARORING: "hungaroring", SPA: "spa", MONZA: "monza", SINGAPORE: "singapore",
    SUZUKA: "suzuka", ABU_DHABI: "abu-dhabi", TEXAS: "texas", BRAZIL: "brazil",
    AUSTRIA: "austria", AUSTRIA_REVERSE: "austria", MEXICO: "mexico",
    BAKU_AZERBAIJAN: "baku-azerbaijan", ZANDVOORT: "zandvoort", ZANDVOORT_REVERSE: "zandvoort",
    IMOLA: "imola", JEDDAH: "jeddah", MIAMI: "miami", LAS_VEGAS: "las-vegas", LOSAIL: "losail"
  };

  // 2026's 22-car grid (11 teams) advances top 16 from Q1/SQ1, top 10 from Q2/SQ2 into Q3 — six
  // eliminated per phase rather than five, unlike the 20-car field this used to assume.
  var QUALI_CUTOFFS = { QUALIFYING_1: 16, QUALIFYING_2: 10, SPRINT_SHOOTOUT_1: 16, SPRINT_SHOOTOUT_2: 10 };

  function teamColor(teamName) {
    var base = String(teamName || "").replace(/_\\d+$/, "");
    var v = TEAM_COLOR_VARS[base];
    return v ? "var(" + v + ")" : "var(--team-fallback)";
  }

  function displayEnum(value) {
    if (!value) return "";
    var m = /^UNKNOWN_(\\d+)$/.exec(value);
    if (m) return "Unknown (" + m[1] + ")";
    return value.split("_").map(function (w) { return w.charAt(0) + w.slice(1).toLowerCase(); }).join(" ");
  }

  function parseMs(v) {
    if (v === null || v === undefined) return null;
    var n = typeof v === "number" ? v : Number(v);
    return isFinite(n) ? n : null;
  }

  function formatLapTime(v) {
    var ms = parseMs(v);
    if (ms === null) return "—";
    var minutes = Math.floor(ms / 60000);
    var seconds = Math.floor((ms % 60000) / 1000);
    var millis = Math.floor(ms % 1000);
    return minutes + ":" + String(seconds).padStart(2, "0") + "." + String(millis).padStart(3, "0");
  }

  function formatGap(ms) {
    var n = parseMs(ms);
    if (n === null || n === 0) return "—";
    return "+" + (n / 1000).toFixed(3);
  }

  function formatClock(totalSeconds) {
    if (totalSeconds === null || totalSeconds === undefined) return "—";
    var s = Math.max(0, Math.round(totalSeconds));
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return m + ":" + String(sec).padStart(2, "0");
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

  function driverCode(name) {
    return (name || "???").replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase() || "???";
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function emptyState() {
    return '<div class="empty">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
      '<h1>No Live Session</h1>' +
      '<p>Nothing is currently being tracked. This page updates automatically the moment a practice, qualifying, or race session starts.</p>' +
      '</div>';
  }

  function renderHeader(data) {
    var s = data.session, t = data.track, tl = data.timeline;
    var sessionLabel = displayEnum(s.session_type);
    var trackLabel = t ? (t.display_name + " — " + t.country) : displayEnum(String(s.track_id));
    var stats = "";
    var totalLaps = (tl && tl.total_laps) || s.total_laps;
    if (totalLaps) {
      stats += '<div class="stat"><div class="value">' + (data.currentLap != null ? data.currentLap : "—") +
        " / " + totalLaps + '</div><div class="label">Lap</div></div>';
    }
    if (tl && tl.session_time_left != null) {
      stats += '<div class="stat"><div class="value" id="clock">' + formatClock(tl.session_time_left) +
        '</div><div class="label">Remaining</div></div>';
    }
    return '<div class="header">' +
      '<div class="header-left">' +
        '<div><span class="live-badge"><span class="dot"></span>LIVE</span></div>' +
        '<div><div class="session-type">' + escapeHtml(sessionLabel) + '</div>' +
        '<div class="track-line">' + escapeHtml(trackLabel) + '</div></div>' +
      '</div>' +
      '<div class="header-right">' + stats + '</div>' +
    '</div>';
  }

  function renderStatusStrip(tl) {
    if (!tl) return "";
    var pills = [];
    pills.push('<span class="pill">' + displayEnum(tl.weather_state) + " — Track " + tl.weather_track_temp + "°C / Air " + tl.weather_air_temp + "°C</span>");
    if (tl.safety_car_status && tl.safety_car_status !== "NONE") {
      pills.push('<span class="pill safety">' + displayEnum(tl.safety_car_status) + '</span>');
    }
    if (Array.isArray(tl.marshal_zone_flags) && tl.marshal_zone_flags.some(function (f) { return f === "YELLOW"; })) {
      pills.push('<span class="pill warn">Yellow Flag</span>');
    }
    return '<div class="status-strip">' + pills.join("") + '</div>';
  }

  function currentLapFraction(driver, trackLength) {
    if (!trackLength || driver.lap_distance == null) return null;
    var f = driver.lap_distance / trackLength;
    return ((f % 1) + 1) % 1;
  }

  function pointAtFraction(zones, f) {
    if (!zones.length) return null;
    var zone = null;
    for (var i = 0; i < zones.length; i++) {
      if (f >= zones[i].start && f < zones[i].end) { zone = zones[i]; break; }
    }
    if (!zone) zone = f < zones[0].start ? zones[0] : zones[zones.length - 1];
    var span = (zone.end - zone.start) || 1;
    var t = Math.min(1, Math.max(0, (f - zone.start) / span));
    return zone.el.getPointAtLength(t * zone.len);
  }

  function loadTrackSvg(slug) {
    if (svgCache[slug]) return svgCache[slug];
    var p = fetch("/images/track-layouts/" + slug + ".svg")
      .then(function (r) { return r.ok ? r.text() : null; });
    svgCache[slug] = p;
    return p;
  }

  var mapState = { slug: null, zones: null };

  function ensureTrackMap(container, track) {
    var slug = track ? TRACK_SLUGS[track.name] : null;
    if (!slug) {
      container.innerHTML = '<div class="no-map">Track map unavailable for this circuit.</div>';
      mapState = { slug: null, zones: null };
      return Promise.resolve();
    }
    if (mapState.slug === slug) return Promise.resolve();
    return loadTrackSvg(slug).then(function (svgText) {
      if (!svgText) {
        container.innerHTML = '<div class="no-map">Track map unavailable for this circuit.</div>';
        mapState = { slug: null, zones: null };
        return;
      }
      container.innerHTML = svgText.replace("<svg ", '<svg class="layout" ');
      var svg = container.querySelector("svg.layout");
      var paths = Array.prototype.slice.call(svg.querySelectorAll("path.zone"));
      var zones = paths.map(function (el) {
        return { el: el, start: parseFloat(el.dataset.start), end: parseFloat(el.dataset.end), len: el.getTotalLength() };
      }).sort(function (a, b) { return a.start - b.start; });
      mapState = { slug: slug, zones: zones };
    });
  }

  function renderDots(container, drivers, track) {
    var svg = container.querySelector("svg.layout");
    if (!svg || !mapState.zones) return;
    var rect = svg.getBoundingClientRect();
    var vb = svg.viewBox.baseVal;
    var scaleX = rect.width / vb.width, scaleY = rect.height / vb.height;

    var existing = {};
    Array.prototype.forEach.call(container.querySelectorAll(".car-dot"), function (el) {
      existing[el.dataset.userId] = el;
    });

    drivers.forEach(function (d) {
      var f = currentLapFraction(d, track ? track.track_length : null);
      var pt = f === null ? null : pointAtFraction(mapState.zones, f);
      var el = existing[d.user_id];
      if (!el) {
        el = document.createElement("div");
        el.className = "car-dot";
        el.dataset.userId = String(d.user_id);
        container.appendChild(el);
      } else {
        delete existing[d.user_id];
      }
      el.style.background = teamColor(d.team_name);
      el.title = d.driver_name + " — P" + (d.position != null ? d.position : "—");
      el.textContent = d.position != null ? String(d.position) : "";
      if (pt) {
        el.style.display = "grid";
        el.style.left = (pt.x * scaleX) + "px";
        el.style.top = (pt.y * scaleY) + "px";
      } else {
        el.style.display = "none";
      }
    });

    Object.keys(existing).forEach(function (id) { existing[id].remove(); });
  }

  function renderLeaderboard(data) {
    var drivers = data.drivers.slice();
    var sessionFastest = null;
    drivers.forEach(function (d) {
      var ms = parseMs(d.best_lap_time_ms);
      if (ms !== null && (sessionFastest === null || ms < sessionFastest)) sessionFastest = ms;
    });

    var cutoff = QUALI_CUTOFFS[data.session.session_type];
    var rows = "";
    drivers.forEach(function (d, i) {
      if (cutoff && i === cutoff && drivers.length > cutoff) {
        rows += '<tr class="cutoff-row"><td colspan="7"><span class="cutoff-label">CUTOFF — TOP ' + cutoff + ' ADVANCE</span></td></tr>';
      }

      var retired = d.result_status === "RETIRED" || d.result_status === "DISQUALIFIED" || d.result_status === "DID_NOT_FINISH";
      var lastMs = parseMs(d.last_lap_time_ms);
      var bestMs = parseMs(d.best_lap_time_ms);
      var lapClass = "lap-time";
      if (sessionFastest !== null && lastMs === sessionFastest) lapClass += " session-fastest";
      else if (bestMs !== null && lastMs === bestMs) lapClass += " personal-best";

      var badges = "";
      if (d.pit_status === "PITTING" || d.pit_status === "IN_PIT_AREA") badges += '<span class="badge pit">PIT</span> ';
      if (d.overtake_active) badges += '<span class="badge boost">OVERTAKE</span> ';
      if (d.driver_status === "OUT_LAP") badges += '<span class="badge out">OUT</span> ';
      if (retired) badges += '<span class="badge out">' + displayEnum(d.result_status) + '</span> ';

      rows += '<tr class="' + (retired ? "retired" : "") + '">' +
        '<td class="pos">' + (d.position != null ? d.position : "—") + '</td>' +
        '<td><div class="driver-cell"><span class="team-bar" style="background:' + teamColor(d.team_name) + '"></span>' +
          '<span class="driver-name">' + escapeHtml(d.driver_name) + '</span>' +
          '<span class="num-tag">#' + d.race_number + '</span></div></td>' +
        '<td class="mono">' + formatGap(d.gap_to_leader_ms) + '</td>' +
        '<td class="mono">' + formatGap(d.gap_to_car_ahead_ms) + '</td>' +
        '<td class="mono ' + lapClass + '">' + formatLapTime(d.last_lap_time_ms) + '</td>' +
        '<td><span class="tyre ' + tyreClass(d.visual_tyre_compound) + '">' + tyreLetter(d.visual_tyre_compound) +
          '</span> <span class="mono">' + (d.tyres_age_laps != null ? d.tyres_age_laps : "—") + '</span></td>' +
        '<td>' + badges + '</td>' +
      '</tr>';
    });

    return '<div class="panel">' +
      '<h2>Leaderboard</h2>' +
      '<table class="board"><thead><tr>' +
      '<th>Pos</th><th>Driver</th><th>Gap</th><th>Int</th><th>Last Lap</th><th>Tyre</th><th></th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table>' +
    '</div>';
  }

  function renderFeed(feed) {
    if (!feed.length) {
      return '<div class="panel feed"><h2>Race Director</h2><div class="feed-empty">No events yet.</div></div>';
    }
    var items = feed.map(function (item) {
      return '<li><span class="feed-dot ' + item.kind + '"></span>' +
        '<span class="feed-time">' + formatClock(item.sessionTime) + '</span>' +
        '<span>' + escapeHtml(item.message) + '</span></li>';
    }).join("");
    return '<div class="panel feed"><h2>Race Director</h2><ul class="feed-list">' + items + '</ul></div>';
  }

  var lastSessionUid = null;

  function render(data) {
    if (!data.live || !data.session) {
      app.innerHTML = emptyState();
      lastSessionUid = null;
      return;
    }

    if (data.session.session_uid !== lastSessionUid) {
      app.innerHTML =
        '<div class="dashboard">' +
          '<div id="header"></div>' +
          '<div id="status"></div>' +
          '<div class="grid">' +
            '<div class="panel"><h2>Track Map</h2><div class="track-map-wrap" id="map"></div></div>' +
            '<div id="board"></div>' +
            '<div id="feed"></div>' +
          '</div>' +
        '</div>';
      lastSessionUid = data.session.session_uid;
    }

    document.getElementById("header").innerHTML = renderHeader(data);
    document.getElementById("status").innerHTML = renderStatusStrip(data.timeline);
    document.getElementById("board").innerHTML = renderLeaderboard(data);
    document.getElementById("feed").innerHTML = renderFeed(data.feed);

    var mapContainer = document.getElementById("map");
    ensureTrackMap(mapContainer, data.track).then(function () {
      renderDots(mapContainer, data.drivers, data.track);
    });
  }

  function poll() {
    fetch("/api/live")
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () {
        if (!lastSessionUid) app.innerHTML = emptyState();
      })
      .then(function () { setTimeout(poll, POLL_MS); });
  }

  poll();
})();
`;
