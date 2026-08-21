import { describe, it, expect, vi, afterEach } from "vitest";
import { env as workerEnv } from "cloudflare:test";
import {
  dispatchInteraction,
  InteractionResponseType,
  InteractionType,
  type CommandDefinition,
  type ComponentDefinition,
  type Interaction,
} from "../../src/discord/interactions";
import type { BotEnv } from "../../src/env";

/**
 * `dispatchInteraction` opens a connection through `connect(env)` for every
 * non-PING interaction, so the real HYPERDRIVE binding has to be present even
 * though none of these handlers issue a query — `postgres` is lazy, so
 * constructing and ending the client never touches the database.
 */
const env = { ...workerEnv } as unknown as BotEnv;

function interaction(overrides: Partial<Interaction>): Interaction {
  return {
    id: "i-1",
    token: "tok-1",
    application_id: "app-1",
    type: InteractionType.APPLICATION_COMMAND,
    ...overrides,
  };
}

function collectWaits() {
  const promises: Array<Promise<unknown>> = [];
  return {
    waitUntil: (p: Promise<unknown>) => void promises.push(p),
    settled: () => Promise.allSettled(promises),
  };
}

/** Captures the PATCH a deferred handler makes to fill in its loading state. */
function stubDiscord() {
  const calls: Array<{ method: string; url: string; body: unknown }> = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit) => {
    calls.push({
      method: init.method ?? "GET",
      url,
      body: init.body ? JSON.parse(init.body as string) : null,
    });
    return new Response(JSON.stringify({ id: "m-1", channel_id: "c-1" }), { status: 200 });
  });
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

const registry = (commands: CommandDefinition[], components: ComponentDefinition[] = []) => ({
  commands,
  components,
});

describe("dispatchInteraction", () => {
  it("answers PING with PONG without touching the database", async () => {
    const waits = collectWaits();
    const response = await dispatchInteraction(
      interaction({ type: InteractionType.PING }),
      env,
      waits.waitUntil,
      registry([])
    );

    expect(response).toEqual({ type: InteractionResponseType.PONG });
  });

  it("defers, then edits the original message with the handler's content", async () => {
    const calls = stubDiscord();
    const waits = collectWaits();

    const response = await dispatchInteraction(
      interaction({ data: { name: "results" } }),
      env,
      waits.waitUntil,
      registry([
        { name: "results", description: "", deferred: true, handler: async () => "P1 Verstappen" },
      ])
    );

    expect(response.type).toBe(InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE);

    await waits.settled();
    const patch = calls.find((c) => c.method === "PATCH");
    expect(patch?.url).toContain("/webhooks/app-1/tok-1/messages/@original");
    expect(patch?.body).toEqual({ content: "P1 Verstappen" });
  });

  it("reports a failing deferred handler in the message rather than hanging", async () => {
    const calls = stubDiscord();
    const waits = collectWaits();

    await dispatchInteraction(
      interaction({ data: { name: "boom" } }),
      env,
      waits.waitUntil,
      registry([
        {
          name: "boom",
          description: "",
          deferred: true,
          handler: async () => {
            throw new Error("query blew up");
          },
        },
      ])
    );
    await waits.settled();

    const patch = calls.find((c) => c.method === "PATCH");
    expect((patch?.body as { content: string }).content).toContain("Something went wrong");
  });

  it("marks an ephemeral deferral so only the invoker sees the loading state", async () => {
    stubDiscord();
    const waits = collectWaits();

    const response = await dispatchInteraction(
      interaction({ data: { name: "session" } }),
      env,
      waits.waitUntil,
      registry([
        {
          name: "session",
          description: "",
          deferred: true,
          ephemeral: true,
          handler: async () => "ok",
        },
      ])
    );
    await waits.settled();

    expect(response.data).toEqual({ flags: 64 });
  });

  it("routes a component click by custom_id prefix", async () => {
    stubDiscord();
    const waits = collectWaits();

    const response = await dispatchInteraction(
      interaction({
        type: InteractionType.MESSAGE_COMPONENT,
        data: { custom_id: "laps:page:2" },
      }),
      env,
      waits.waitUntil,
      registry(
        [],
        [{ prefix: "laps:", deferred: true, handler: async (ctx) => ctx.interaction.data!.custom_id! }]
      )
    );
    expect(response.type).toBe(InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE);
    await waits.settled();
  });

  it("explains itself for an unregistered command instead of timing out", async () => {
    const waits = collectWaits();
    const response = await dispatchInteraction(
      interaction({ data: { name: "nope" } }),
      env,
      waits.waitUntil,
      registry([])
    );

    expect(response.type).toBe(InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE);
    expect(response.data).toMatchObject({ flags: 64 });
    expect(String(response.data?.content)).toContain("isn't handled");
  });

  it("reads slash-command options and modal fields through the same accessor", async () => {
    stubDiscord();
    const waits = collectWaits();
    const seen: Array<string | undefined> = [];

    await dispatchInteraction(
      interaction({ data: { name: "laps", options: [{ name: "driver", value: 44 }] } }),
      env,
      waits.waitUntil,
      registry([
        {
          name: "laps",
          description: "",
          deferred: true,
          handler: async (ctx) => {
            seen.push(ctx.option("driver"), ctx.option("missing"));
            return "ok";
          },
        },
      ])
    );
    await waits.settled();

    expect(seen).toEqual(["44", undefined]);
  });
});
