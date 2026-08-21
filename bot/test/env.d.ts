import type { BotEnv } from "../src/env";

/**
 * Declaration merging into the global `Cloudflare.Env` that
 * `cloudflare:test`'s `env` is typed as. Without it `env.BOT_STATE` is an
 * `any`-free compile error in tests; with it, a test reaching for a binding
 * fails to compile if `wrangler.jsonc` and `BotEnv` ever disagree.
 */
declare global {
  namespace Cloudflare {
    interface Env extends BotEnv {}
  }
}
