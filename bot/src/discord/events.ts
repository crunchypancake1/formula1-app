/**
 * Inbound webhook events (`/bot/events`). Two differences from interactions:
 * the PING discriminator is type 0, not 1, and every ack is a bare 204 — a
 * JSON body makes Discord retry the delivery.
 */

import type { BotEnv } from "../env";

export const WebhookType = {
  PING: 0,
  EVENT: 1,
} as const;

export interface WebhookEvent {
  type: number;
  event?: {
    type: string;
    timestamp: string;
    data?: Record<string, unknown>;
  };
}

export type EventHandler = (
  data: Record<string, unknown> | undefined,
  env: BotEnv
) => Promise<void>;

/** Keyed by Discord's event type string (`APPLICATION_AUTHORIZED`, …). */
export const EVENT_HANDLERS: Record<string, EventHandler> = {};

/** The caller always answers 204, unknown types included — a non-2xx makes Discord retry. */
export async function dispatchEvent(payload: WebhookEvent, env: BotEnv): Promise<void> {
  if (payload.type !== WebhookType.EVENT || !payload.event) return;

  const handler = EVENT_HANDLERS[payload.event.type];
  if (!handler) {
    console.log(`unhandled webhook event: ${payload.event.type}`);
    return;
  }

  try {
    await handler(payload.event.data, env);
  } catch (e) {
    console.error(`webhook event "${payload.event.type}" failed:`, e);
  }
}
