import type { Env } from "@f1/db";

/**
 * A Secrets Store binding's runtime shape: async `get()`, not a plain string
 * like a `vars` entry — see https://developers.cloudflare.com/secrets-store/.
 */
export interface SecretsStoreSecret {
  get(): Promise<string>;
}

/** Adds the bot's Discord-specific bindings on top of the shared `@f1/db` Env. */
export interface BotEnv extends Env {
  DISCORD_GUILD_ID: string;
  /** Defaults to "active-session" if unset — see `wrangler.jsonc`. */
  DISCORD_CHANNEL_NAME: string;
  DISCORD_ARCHIVE_CATEGORY_ID?: string;
  DISCORD_BOT_TOKEN: SecretsStoreSecret;
}
