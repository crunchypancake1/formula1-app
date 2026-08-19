import { describe, it, expect } from "vitest";
import { readLatestTimeline } from "../../src/queries/timeline";
import { timelineRow } from "../fixtures";

describe("readLatestTimeline", () => {
  it("returns the first row — the query orders by overall_frame_identifier DESC", async () => {
    const rows = [timelineRow({ overall_frame_identifier: 20000, session_time_left: 300 })];

    const timeline = await readLatestTimeline(async () => rows);

    expect(timeline?.overall_frame_identifier).toBe(20000);
    expect(timeline?.session_time_left).toBe(300);
  });

  it("returns null when the session has no timeline rows yet", async () => {
    expect(await readLatestTimeline(async () => [])).toBeNull();
  });
});
