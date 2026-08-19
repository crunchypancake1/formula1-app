import type {
  ClassifiedDriver,
  QualifyingClassificationRow,
  RaceClassificationRow,
  Sql,
} from "@f1/db";

export type RaceResult = ClassifiedDriver<RaceClassificationRow>;
export type QualifyingResult = ClassifiedDriver<QualifyingClassificationRow>;

/** Pure over its query function so it can be tested without a database. */
export async function readRaceClassification(
  query: () => Promise<RaceResult[]>
): Promise<RaceResult[]> {
  return query();
}

export async function readQualifyingClassification(
  query: () => Promise<QualifyingResult[]>
): Promise<QualifyingResult[]> {
  return query();
}

/**
 * Drivers who did not reach the flag. `result_reason` is the F1 26 addition that
 * says *why*; it is null on sessions recorded before the game started sending it,
 * so `result_status` stays the source of truth for whether they finished.
 */
export function nonFinishers(results: RaceResult[]): RaceResult[] {
  return results.filter((r) => r.result_status !== "FINISHED");
}

export function raceClassification(sql: Sql, sessionUid: string) {
  return readRaceClassification(
    () => sql<RaceResult[]>`
      SELECT rc.*, u.driver_name, u.discord_id
        FROM telemetry.race_classification rc
        JOIN identity.users u ON u.id = rc.user_id
       WHERE rc.session_uid = ${sessionUid}
       ORDER BY rc.position
    `
  );
}

export function qualifyingClassification(sql: Sql, sessionUid: string) {
  return readQualifyingClassification(
    () => sql<QualifyingResult[]>`
      SELECT qc.*, u.driver_name, u.discord_id
        FROM telemetry.qualifying_classification qc
        JOIN identity.users u ON u.id = qc.user_id
       WHERE qc.session_uid = ${sessionUid}
       ORDER BY qc.position
    `
  );
}
