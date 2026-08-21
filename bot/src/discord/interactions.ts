/**
 * Inbound interactions: slash commands, components, modals, autocomplete.
 *
 * Discord fails an interaction with no response inside 3s, which
 * Hyperdrive-over-tunnel does not reliably beat — so a `deferred` handler gets
 * an immediate type-5 ACK and edits its message afterwards from `waitUntil`.
 */

import { connect, type Sql } from "@f1/db";
import { editInteractionResponse } from "./client";
import type { BotEnv } from "../env";

/** https://discord.com/developers/docs/interactions/receiving-and-responding */
export const InteractionType = {
  PING: 1,
  APPLICATION_COMMAND: 2,
  MESSAGE_COMPONENT: 3,
  APPLICATION_COMMAND_AUTOCOMPLETE: 4,
  MODAL_SUBMIT: 5,
} as const;

export const InteractionResponseType = {
  PONG: 1,
  CHANNEL_MESSAGE_WITH_SOURCE: 4,
  DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE: 5,
  DEFERRED_UPDATE_MESSAGE: 6,
  UPDATE_MESSAGE: 7,
  APPLICATION_COMMAND_AUTOCOMPLETE_RESULT: 8,
  MODAL: 9,
} as const;

/** Message flag `1 << 6` — only the invoking user sees the reply. */
export const EPHEMERAL = 64;

export interface InteractionOption {
  name: string;
  value?: string | number | boolean;
  options?: InteractionOption[];
  focused?: boolean;
}

export interface Interaction {
  id: string;
  token: string;
  type: number;
  /** Present on every interaction, which is why the app id needs no `var`. */
  application_id: string;
  data?: {
    name?: string;
    custom_id?: string;
    options?: InteractionOption[];
    components?: Array<{ components?: Array<{ custom_id: string; value: string }> }>;
  };
  member?: { user?: { id: string; username: string } };
  user?: { id: string; username: string };
}

export interface InteractionResponse {
  type: number;
  data?: Record<string, unknown>;
}

/** `sql` is opened and closed by the dispatcher; handlers never manage it. */
export interface HandlerContext {
  interaction: Interaction;
  env: BotEnv;
  sql: Sql;
  /** Named slash-command option, or the `custom_id` suffix for components. */
  option(name: string): string | undefined;
}

/** Handlers return message content; `null` means "nothing to say". */
export type Handler = (ctx: HandlerContext) => Promise<string | null>;

export interface CommandDefinition {
  name: string;
  description: string;
  options?: unknown[];
  /** Required for anything that queries Postgres — see the module comment. */
  deferred?: boolean;
  /** Reply visible only to the invoking user. */
  ephemeral?: boolean;
  handler: Handler;
}

export interface ComponentDefinition {
  /** Matched against the start of the component's `custom_id`. */
  prefix: string;
  deferred?: boolean;
  ephemeral?: boolean;
  handler: Handler;
}

function optionReader(interaction: Interaction): (name: string) => string | undefined {
  const options = interaction.data?.options ?? [];
  const modalFields = (interaction.data?.components ?? []).flatMap((row) => row.components ?? []);

  return (name) => {
    const option = options.find((o) => o.name === name);
    if (option?.value !== undefined) return String(option.value);

    const field = modalFields.find((f) => f.custom_id === name);
    return field?.value;
  };
}

export function message(content: string, ephemeral = false): InteractionResponse {
  return {
    type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
    data: { content, flags: ephemeral ? EPHEMERAL : 0 },
  };
}

/** Runs a deferred handler and edits its message; a throw becomes a visible error, not a stuck spinner. */
async function completeDeferred(
  def: { handler: Handler; ephemeral?: boolean },
  interaction: Interaction,
  env: BotEnv
): Promise<void> {
  const sql = connect(env);
  try {
    const content = await def.handler({
      interaction,
      env,
      sql,
      option: optionReader(interaction),
    });
    if (content !== null) {
      await editInteractionResponse(interaction.application_id, interaction.token, content);
    }
  } catch (e) {
    console.error(`interaction "${interaction.data?.name ?? interaction.type}" failed:`, e);
    await editInteractionResponse(
      interaction.application_id,
      interaction.token,
      "Something went wrong handling that. The error is in the Worker logs."
    ).catch(() => {});
  } finally {
    await sql.end();
  }
}

/**
 * Turns a verified interaction into the response for the POST. Deferred work
 * outlives this call via `waitUntil` — the interaction token is valid 15 min.
 */
export async function dispatchInteraction(
  interaction: Interaction,
  env: BotEnv,
  waitUntil: (promise: Promise<unknown>) => void,
  registry: {
    commands: CommandDefinition[];
    components: ComponentDefinition[];
  }
): Promise<InteractionResponse> {
  if (interaction.type === InteractionType.PING) {
    return { type: InteractionResponseType.PONG };
  }

  const definition =
    interaction.type === InteractionType.APPLICATION_COMMAND
      ? registry.commands.find((c) => c.name === interaction.data?.name)
      : interaction.type === InteractionType.MESSAGE_COMPONENT
        ? registry.components.find((c) => interaction.data?.custom_id?.startsWith(c.prefix))
        : undefined;

  if (!definition) {
    return message("That interaction isn't handled by this bot (yet).", true);
  }

  if (definition.deferred) {
    waitUntil(completeDeferred(definition, interaction, env));
    return {
      type: InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
      data: { flags: definition.ephemeral ? EPHEMERAL : 0 },
    };
  }

  const sql = connect(env);
  try {
    const content = await definition.handler({
      interaction,
      env,
      sql,
      option: optionReader(interaction),
    });
    return message(content ?? "Done.", definition.ephemeral);
  } finally {
    waitUntil(sql.end());
  }
}
