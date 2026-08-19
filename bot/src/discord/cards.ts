import { displayEnum, formatLapTime, type SessionBest, type SessionRow, type TrackRow } from "@f1/db";
import type { QualifyingResult, RaceResult } from "../queries/results";

/**
 * 2026's 22-car grid (11 teams) advances top 16 from Q1/SQ1, top 10 from
 * Q2/SQ2 into Q3 — ported from `web/worker/dashboard.ts`'s QUALI_CUTOFFS
 * rather than re-derived, since both read the same session_type values.
 */
const QUALI_CUTOFFS: Partial<Record<string, number>> = {
  QUALIFYING_1: 16,
  QUALIFYING_2: 10,
  SPRINT_SHOOTOUT_1: 16,
  SPRINT_SHOOTOUT_2: 10,
};

const NON_FINISHED_STATUSES = new Set(["RETIRED", "DISQUALIFIED", "DID_NOT_FINISH", "NOT_CLASSIFIED"]);

function trackLine(track: TrackRow | null, session: SessionRow): string {
  return track ? `${track.display_name} — ${track.country}` : displayEnum(String(session.track_id));
}

function pad(value: string, width: number): string {
  return value.length >= width ? value.slice(0, width) : value.padEnd(width);
}

function padStart(value: string, width: number): string {
  return value.length >= width ? value.slice(0, width) : value.padStart(width);
}

/**
 * Formats `total_race_time` — a FLOAT column of seconds, unlike every other
 * time in this schema which is milliseconds — as `m:ss.mmm` for the leader,
 * or a `+`-prefixed gap for everyone else.
 */
function formatRaceTime(totalSeconds: number, leaderSeconds: number, isLeader: boolean): string {
  if (isLeader) return formatLapTime(Math.round(totalSeconds * 1000));
  return `+${(totalSeconds - leaderSeconds).toFixed(3)}`;
}

/**
 * Header shared by every card: session type, track, and (for non-race
 * sessions still in progress) a Discord-native countdown that updates
 * client-side with zero further bot polling. Races never show a countdown —
 * they are not time-bounded the same way a practice or qualifying clock is.
 */
export function cardHeader(
  session: SessionRow,
  track: TrackRow | null,
  countdownUnix: number | null
): string {
  const lines = [`**${displayEnum(session.session_type)}** — ${trackLine(track, session)}`];
  if (countdownUnix !== null) {
    lines.push(`Ends <t:${countdownUnix}:R>`);
  }
  return lines.join("\n");
}

/** Placeholder card posted the moment a session starts, before any result exists yet. */
export function placeholderCard(
  session: SessionRow,
  track: TrackRow | null,
  countdownUnix: number | null
): string {
  const status = session.session_type.includes("RACE") ? "In progress…" : "Session live…";
  return `${cardHeader(session, track, countdownUnix)}\n${status}`;
}

/** Practice card: best lap and sector summary, since there is no classification for practice. */
export function practiceCard(
  session: SessionRow,
  track: TrackRow | null,
  bests: readonly SessionBest[]
): string {
  const sorted = [...bests].sort((a, b) => {
    const aMs = a.best_lap_time_ms ?? Infinity;
    const bMs = b.best_lap_time_ms ?? Infinity;
    return aMs - bMs;
  });

  const rows = sorted.map((b, i) => {
    const pos = padStart(String(i + 1), 2);
    const name = pad(b.driver_name, 18);
    const lap = padStart(formatLapTime(b.best_lap_time_ms), 10);
    const s1 = padStart(formatLapTime(b.best_sector1_time_ms), 9);
    const s2 = padStart(formatLapTime(b.best_sector2_time_ms), 9);
    const s3 = padStart(formatLapTime(b.best_sector3_time_ms), 9);
    return `${pos} ${name} ${lap} ${s1} ${s2} ${s3}`;
  });

  const table = sorted.length
    ? [
        `${padStart("#", 2)} ${pad("Driver", 18)} ${padStart("Best Lap", 10)} ${padStart(
          "S1",
          9
        )} ${padStart("S2", 9)} ${padStart("S3", 9)}`,
        ...rows,
      ].join("\n")
    : "No laps set yet.";

  return `${cardHeader(session, track, null)}\n\`\`\`\n${table}\n\`\`\``;
}

/** Qualifying card: final positions, best lap, and the elimination cutoff for Q1/Q2/SQ1/SQ2. */
export function qualifyingCard(
  session: SessionRow,
  track: TrackRow | null,
  results: readonly QualifyingResult[]
): string {
  const cutoff = QUALI_CUTOFFS[session.session_type];

  const lines: string[] = [
    `${padStart("Pos", 3)} ${pad("Driver", 18)} ${padStart("Best Lap", 10)}`,
  ];
  results.forEach((r, i) => {
    if (cutoff && i === cutoff) {
      lines.push(`--- CUTOFF — TOP ${cutoff} ADVANCE ---`);
    }
    const pos = padStart(String(r.position), 3);
    const name = pad(r.driver_name, 18);
    const lap = padStart(formatLapTime(r.best_lap_time_ms), 10);
    lines.push(`${pos} ${name} ${lap}`);
  });

  const table = results.length ? lines.join("\n") : "No classified result yet.";

  return `${cardHeader(session, track, null)}\n\`\`\`\n${table}\n\`\`\``;
}

/** Race card: final classification, gap to the leader, and DNFs with their reason. */
export function raceCard(
  session: SessionRow,
  track: TrackRow | null,
  results: readonly RaceResult[]
): string {
  const finishers = results.filter((r) => !NON_FINISHED_STATUSES.has(r.result_status));
  const nonFinishers = results.filter((r) => NON_FINISHED_STATUSES.has(r.result_status));
  const leaderSeconds = finishers[0]?.total_race_time ?? 0;

  const lines: string[] = [
    `${padStart("Pos", 3)} ${pad("Driver", 18)} ${padStart("Time/Gap", 12)} ${padStart("Pts", 3)}`,
  ];
  finishers.forEach((r, i) => {
    const pos = padStart(String(r.position), 3);
    const name = pad(r.driver_name, 18);
    const time = padStart(formatRaceTime(r.total_race_time, leaderSeconds, i === 0), 12);
    const pts = padStart(r.game_points != null ? String(r.game_points) : "—", 3);
    lines.push(`${pos} ${name} ${time} ${pts}`);
  });

  const table = finishers.length ? lines.join("\n") : "No classified result yet.";

  const dnfLines = nonFinishers.map(
    (r) => `${r.driver_name} — ${displayEnum(r.result_reason ?? r.result_status)}`
  );
  const dnfBlock = dnfLines.length ? `\n\n**DNF / DSQ**\n${dnfLines.join("\n")}` : "";

  return `${cardHeader(session, track, null)}\n\`\`\`\n${table}\n\`\`\`${dnfBlock}`;
}

/** Dispatches to the right card builder for a finalized session's type. */
export function finalCardFor(
  session: SessionRow,
  track: TrackRow | null,
  data: { bests?: readonly SessionBest[]; qualifying?: readonly QualifyingResult[]; race?: readonly RaceResult[] }
): string {
  if (session.session_type.includes("RACE")) {
    return raceCard(session, track, data.race ?? []);
  }
  if (session.session_type.includes("QUALIFYING") || session.session_type.includes("SHOOTOUT")) {
    return qualifyingCard(session, track, data.qualifying ?? []);
  }
  return practiceCard(session, track, data.bests ?? []);
}
