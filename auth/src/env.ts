/**
 * A Secrets Store binding's runtime shape: async `get()`, not a plain string
 * like a `vars` entry — see https://developers.cloudflare.com/secrets-store/.
 */
export interface SecretsStoreSecret {
  get(): Promise<string>;
}

/** This Worker never touches the database — no `@f1/db` `Env` here, unlike `bot`/`web`. */
export interface AuthEnv {
  DISCORD_OAUTH_CLIENT_ID: string;
  ACCESS_CLIENT_ID: string;
  ACCESS_TEAM_DOMAIN: string;
  OIDC_ISSUER: string;
  DISCORD_OAUTH_CLIENT_SECRET: SecretsStoreSecret;
  ACCESS_CLIENT_SECRET: SecretsStoreSecret;
  OIDC_SIGNING_KEY: SecretsStoreSecret;
  /** The same KV namespace as `bot`'s `BOT_STATE` — read-only here, `bot`'s cron tick owns the writes. */
  BOT_STATE: KVNamespace;
}
