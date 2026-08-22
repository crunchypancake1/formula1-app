import type { Sql } from "@f1/db";
import type { Viewer } from "./access";
import { memberNickname } from "./discordRoster";
import { matchDriver } from "./matching";
import { roster } from "./queries/entries";

export interface ResolvedDriver {
  userId: number;
  driverName: string;
}

/**
 * Fuzzy-matches the viewer against the live session's roster at runtime —
 * nothing is persisted or looked up from a prior link. Every request scores
 * the viewer's Discord handle and server nickname against each driver name
 * fresh; a confident match is returned, otherwise null (no button, no
 * picker). Shared by `/api/live`'s `you` block and `/api/me`.
 */
export async function resolveViewerDriver(
  sql: Sql,
  kv: KVNamespace,
  sessionUid: string,
  viewer: Viewer
): Promise<ResolvedDriver | null> {
  const sessionRoster = await roster(sql, sessionUid);
  const nickname = await memberNickname(kv, viewer.discordId);

  return matchDriver(
    viewer.username,
    nickname,
    sessionRoster.map((r) => ({ userId: r.user_id, driverName: r.driver_name }))
  );
}
