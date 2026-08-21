/**
 * The slash-command registry — adding a command is one object here.
 * Anything reading Postgres must be `deferred: true` (see `interactions.ts`).
 */

import { finalCardFor, placeholderCard } from "./cards";
import { currentApplicationId, putGuildCommands } from "./client";
import type { CommandDefinition, ComponentDefinition, HandlerContext } from "./interactions";
import { sessionBests } from "../queries/laps";
import { qualifyingClassification, raceClassification } from "../queries/results";
import { latestSession } from "../queries/sessions";
import { latestTimeline } from "../queries/timeline";
import { trackById } from "../queries/tracks";

async function resultDataFor(ctx: HandlerContext, sessionUid: string, sessionType: string) {
  if (sessionType.includes("RACE")) {
    return { race: await raceClassification(ctx.sql, sessionUid) };
  }
  if (sessionType.includes("QUALIFYING") || sessionType.includes("SHOOTOUT")) {
    return { qualifying: await qualifyingClassification(ctx.sql, sessionUid) };
  }
  return { bests: await sessionBests(ctx.sql, sessionUid) };
}

export const COMMANDS: CommandDefinition[] = [
  {
    name: "session",
    description: "Show the session currently being recorded",
    deferred: true,
    ephemeral: true,
    async handler(ctx) {
      const session = await latestSession(ctx.sql);
      if (!session) return "No session has been recorded yet.";

      const track = await trackById(ctx.sql, session.track_id);
      const isRace = session.session_type.includes("RACE");
      const timeline = isRace ? null : await latestTimeline(ctx.sql, session.session_uid);
      const countdownUnix = timeline
        ? Math.round(Date.now() / 1000 + timeline.session_time_left)
        : null;

      return placeholderCard(session, track, countdownUnix);
    },
  },
  {
    name: "results",
    description: "Show the classification for the most recent session",
    deferred: true,
    async handler(ctx) {
      const session = await latestSession(ctx.sql);
      if (!session) return "No session has been recorded yet.";

      const track = await trackById(ctx.sql, session.track_id);
      const data = await resultDataFor(ctx, session.session_uid, session.session_type);
      return finalCardFor(session, track, data);
    },
  },
];

/** Button/select-menu handlers, matched by `custom_id` prefix. */
export const COMPONENTS: ComponentDefinition[] = [];

/** The subset Discord wants at registration. */
function toSchema(command: CommandDefinition) {
  return {
    name: command.name,
    description: command.description,
    options: command.options ?? [],
  };
}

const SYNC_KEY = "commands:v1";

async function fingerprint(): Promise<string> {
  const json = JSON.stringify(COMMANDS.map(toSchema));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(json));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Re-registers the command list whenever it differs from the hash in KV.
 * Not time-based, unlike `roleStore.ts` — commands change only when this file
 * does. Deleting the KV key forces a resync.
 */
export async function ensureCommands(
  kv: KVNamespace,
  token: string,
  guildId: string
): Promise<boolean> {
  if (!guildId) {
    throw new Error("DISCORD_GUILD_ID is unset — refusing to register commands");
  }

  const current = await fingerprint();
  if ((await kv.get(SYNC_KEY)) === current) return false;

  const applicationId = await currentApplicationId(token);
  await putGuildCommands(token, applicationId, guildId, COMMANDS.map(toSchema));
  await kv.put(SYNC_KEY, current);
  return true;
}
