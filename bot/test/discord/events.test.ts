import { describe, it, expect, vi, afterEach } from "vitest";
import { dispatchEvent, EVENT_HANDLERS, WebhookType } from "../../src/discord/events";
import type { BotEnv } from "../../src/env";

const env = {} as BotEnv;

afterEach(() => {
  for (const key of Object.keys(EVENT_HANDLERS)) delete EVENT_HANDLERS[key];
  vi.restoreAllMocks();
});

describe("dispatchEvent", () => {
  it("ignores the PING type — the caller answers it with a bare 204", async () => {
    const handler = vi.fn(async () => {});
    EVENT_HANDLERS.APPLICATION_AUTHORIZED = handler;

    await dispatchEvent({ type: WebhookType.PING }, env);
    expect(handler).not.toHaveBeenCalled();
  });

  it("routes an event to its handler with the payload data", async () => {
    const handler = vi.fn(async () => {});
    EVENT_HANDLERS.APPLICATION_AUTHORIZED = handler;

    await dispatchEvent(
      {
        type: WebhookType.EVENT,
        event: {
          type: "APPLICATION_AUTHORIZED",
          timestamp: "2026-08-21T00:00:00Z",
          data: { user: { id: "u-1" } },
        },
      },
      env
    );

    expect(handler).toHaveBeenCalledWith({ user: { id: "u-1" } }, env);
  });

  it("swallows a throwing handler so Discord doesn't retry the delivery", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    EVENT_HANDLERS.ENTITLEMENT_CREATE = async () => {
      throw new Error("nope");
    };

    await expect(
      dispatchEvent(
        {
          type: WebhookType.EVENT,
          event: { type: "ENTITLEMENT_CREATE", timestamp: "2026-08-21T00:00:00Z" },
        },
        env
      )
    ).resolves.toBeUndefined();
  });

  it("logs and moves on for an event type nothing handles", async () => {
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    await dispatchEvent(
      { type: WebhookType.EVENT, event: { type: "QUEST_USER_ENROLLMENT", timestamp: "x" } },
      env
    );
    expect(log).toHaveBeenCalledWith(expect.stringContaining("QUEST_USER_ENROLLMENT"));
  });
});
