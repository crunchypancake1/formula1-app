import { describe, it, expect } from "vitest";
import {
  readActiveWeekend,
  readPendingSessionMessages,
  readSessionMessage,
} from "../../src/queries/discordState";
import { discordSessionMessageRow, discordWeekendRow } from "../fixtures";

describe("readActiveWeekend", () => {
  it("returns the not-yet-archived weekend", async () => {
    const weekend = await readActiveWeekend(async () => [discordWeekendRow()]);
    expect(weekend?.weekend_link).toBe("weekend-1");
  });

  it("returns null when no weekend is tracked", async () => {
    expect(await readActiveWeekend(async () => [])).toBeNull();
  });
});

describe("readSessionMessage", () => {
  it("returns the tracked message for a session", async () => {
    const message = await readSessionMessage(async () => [discordSessionMessageRow()]);
    expect(message?.message_id).toBe("message-1");
  });

  it("returns null when the session has no card yet", async () => {
    expect(await readSessionMessage(async () => [])).toBeNull();
  });
});

describe("readPendingSessionMessages", () => {
  it("passes unfinalized rows through", async () => {
    const rows = [
      discordSessionMessageRow({ session_uid: "a" }),
      discordSessionMessageRow({ session_uid: "b" }),
    ];
    expect((await readPendingSessionMessages(async () => rows)).map((r) => r.session_uid)).toEqual(
      ["a", "b"]
    );
  });

  it("is empty when nothing is pending", async () => {
    expect(await readPendingSessionMessages(async () => [])).toEqual([]);
  });
});
