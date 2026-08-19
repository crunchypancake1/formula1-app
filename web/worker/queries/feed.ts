import {
  displayEnum,
  formatLapTime,
  type FastestLapEventRow,
  type PenaltyEventRow,
  type RaceControlEventRow,
  type RetirementEventRow,
  type Sql,
} from "@f1/db";

const FEED_LIMIT = 30;

export function raceControlEvents(sql: Sql, sessionUid: string) {
  return sql<RaceControlEventRow[]>`
    SELECT overall_frame_identifier, session_time, event_code,
           safety_car_type, safety_car_event_type, num_lights, drs_disabled_reason
      FROM telemetry.events_race_control
     WHERE session_uid = ${sessionUid}
     ORDER BY overall_frame_identifier DESC
     LIMIT ${FEED_LIMIT}
  `;
}

export function penaltyEvents(sql: Sql, sessionUid: string) {
  return sql<PenaltyEventRow[]>`
    SELECT p.overall_frame_identifier, p.session_time,
           u.driver_name, ou.driver_name AS other_driver_name,
           p.penalty_type, p.infringement_type, p.time_seconds, p.lap_num, p.places_gained
      FROM telemetry.events_penalties p
      JOIN identity.users u        ON u.id = p.user_id
      LEFT JOIN identity.users ou  ON ou.id = p.other_user_id
     WHERE p.session_uid = ${sessionUid}
     ORDER BY p.overall_frame_identifier DESC
     LIMIT ${FEED_LIMIT}
  `;
}

export function retirementEvents(sql: Sql, sessionUid: string) {
  return sql<RetirementEventRow[]>`
    SELECT r.overall_frame_identifier, r.session_time, u.driver_name, r.reason
      FROM telemetry.events_retirements r
      JOIN identity.users u ON u.id = r.user_id
     WHERE r.session_uid = ${sessionUid}
     ORDER BY r.overall_frame_identifier DESC
     LIMIT ${FEED_LIMIT}
  `;
}

export function fastestLapEvents(sql: Sql, sessionUid: string) {
  return sql<FastestLapEventRow[]>`
    SELECT f.overall_frame_identifier, f.session_time, u.driver_name, f.lap_time
      FROM telemetry.events_fastest_laps f
      JOIN identity.users u ON u.id = f.user_id
     WHERE f.session_uid = ${sessionUid}
     ORDER BY f.overall_frame_identifier DESC
     LIMIT ${FEED_LIMIT}
  `;
}

export type FeedKind =
  | "flag"
  | "lights"
  | "drs"
  | "safety-car"
  | "penalty"
  | "retirement"
  | "fastest-lap";

export interface FeedItem {
  frame: number;
  sessionTime: number;
  kind: FeedKind;
  message: string;
}

const SAFETY_CAR_TYPE_LABEL: Record<string, string> = {
  FULL: "Safety Car",
  VIRTUAL: "Virtual Safety Car",
  FORMATION_LAP: "Formation Lap",
};

const SAFETY_CAR_EVENT_LABEL: Record<string, string> = {
  DEPLOYED: "deployed",
  RETURNING: "returning to the pits",
  RETURNED: "in the pit lane",
  RESUME_RACE: "in — racing resumes",
};

function raceControlMessage(row: RaceControlEventRow): string | null {
  switch (row.event_code) {
    case "SSTA":
      return "Session started";
    case "SEND":
      return "Session ended";
    case "LGOT":
      return "Lights out — session underway";
    case "CHQF":
      return "Chequered flag";
    case "RDFL":
      return "Red flag";
    case "DRSE":
      return "DRS enabled";
    case "DRSD":
      return row.drs_disabled_reason
        ? `DRS disabled — ${displayEnum(row.drs_disabled_reason)}`
        : "DRS disabled";
    case "STLG":
      return row.num_lights != null ? `Start lights: ${row.num_lights}` : "Start lights";
    case "SCAR": {
      if (!row.safety_car_type || row.safety_car_type === "NONE") return null;
      const type = SAFETY_CAR_TYPE_LABEL[row.safety_car_type] ?? displayEnum(row.safety_car_type);
      const event = row.safety_car_event_type
        ? (SAFETY_CAR_EVENT_LABEL[row.safety_car_event_type] ??
          displayEnum(row.safety_car_event_type))
        : "";
      return event ? `${type} ${event}` : type;
    }
    default:
      return null;
  }
}

function raceControlKind(row: RaceControlEventRow): FeedKind {
  if (row.event_code === "SCAR") return "safety-car";
  if (row.event_code === "DRSE" || row.event_code === "DRSD") return "drs";
  if (row.event_code === "STLG") return "lights";
  return "flag";
}

function penaltyMessage(row: PenaltyEventRow): string {
  const headline =
    row.time_seconds != null ? `${row.time_seconds}s time penalty` : displayEnum(row.penalty_type);
  const involving = row.other_driver_name ? ` — involving ${row.other_driver_name}` : "";
  return `${headline} — ${row.driver_name} (${displayEnum(row.infringement_type)})${involving}`;
}

function fastestLapMessage(row: FastestLapEventRow): string {
  return `${row.driver_name} sets fastest lap — ${formatLapTime(Math.round(row.lap_time * 1000))}`;
}

/**
 * Merges the four race-control-relevant event tables into one reverse-
 * chronological feed with human-readable messages, ordered by
 * overall_frame_identifier (survives flashbacks, unlike session_time).
 *
 * Pure over its inputs so it can be tested without a database.
 */
export function buildFeed(
  raceControl: RaceControlEventRow[],
  penalties: PenaltyEventRow[],
  retirements: RetirementEventRow[],
  fastestLaps: FastestLapEventRow[]
): FeedItem[] {
  const items: FeedItem[] = [];

  for (const row of raceControl) {
    const message = raceControlMessage(row);
    if (message === null) continue;
    items.push({
      frame: row.overall_frame_identifier,
      sessionTime: row.session_time,
      kind: raceControlKind(row),
      message,
    });
  }

  for (const row of penalties) {
    items.push({
      frame: row.overall_frame_identifier,
      sessionTime: row.session_time,
      kind: "penalty",
      message: penaltyMessage(row),
    });
  }

  for (const row of retirements) {
    items.push({
      frame: row.overall_frame_identifier,
      sessionTime: row.session_time,
      kind: "retirement",
      message: `${row.driver_name} has retired — ${displayEnum(row.reason)}`,
    });
  }

  for (const row of fastestLaps) {
    items.push({
      frame: row.overall_frame_identifier,
      sessionTime: row.session_time,
      kind: "fastest-lap",
      message: fastestLapMessage(row),
    });
  }

  items.sort((a, b) => b.frame - a.frame);
  return items.slice(0, FEED_LIMIT);
}
