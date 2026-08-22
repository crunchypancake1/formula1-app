import type { Env } from "@f1/db";

/** `web`'s full binding set — `@f1/db`'s `Env` plus the Access/Discord additions for `/me`. */
export interface WebEnv extends Env {
  ACCESS_TEAM_DOMAIN: string;
  ACCESS_POLICY_AUD: string;
  /** Read-only: the same KV namespace `bot`'s cron tick owns (`BOT_STATE` in bot/wrangler.jsonc). */
  BOT_STATE: KVNamespace;
}
