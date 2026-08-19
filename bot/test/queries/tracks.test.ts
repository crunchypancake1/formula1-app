import { describe, it, expect } from "vitest";
import { readTrack } from "../../src/queries/tracks";
import { trackRow } from "../fixtures";

describe("readTrack", () => {
  it("returns the matching track", async () => {
    const track = await readTrack(async () => [trackRow({ track_id: 10 })]);
    expect(track?.track_id).toBe(10);
  });

  it("returns null when the track is unknown", async () => {
    expect(await readTrack(async () => [])).toBeNull();
  });
});
