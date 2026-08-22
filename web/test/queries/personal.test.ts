import { describe, it, expect } from "vitest";
import { readPersonalDamage, resolvePersonalFrame } from "../../worker/queries/personal";
import { carDamageRow, personalFrameRow } from "../fixtures";

describe("resolvePersonalFrame", () => {
  it("resolves the viewer's and neighbours' tyre compound codes", () => {
    const frame = resolvePersonalFrame(personalFrameRow());

    expect(frame.actual_tyre_compound).toBe("C1");
    expect(frame.visual_tyre_compound).toBe("SOFT");
    expect(frame.ahead_visual_tyre_compound).toBe("MEDIUM");
    expect(frame.behind_visual_tyre_compound).toBe("HARD");
  });

  it("leaves a null neighbour (P1 has no car ahead) as null, not a resolved code", () => {
    const frame = resolvePersonalFrame(
      personalFrameRow({ ahead_driver_name: null, ahead_visual_tyre_compound: null, ahead_tyres_age_laps: null })
    );

    expect(frame.ahead_driver_name).toBeNull();
    expect(frame.ahead_visual_tyre_compound).toBeNull();
  });

  it("degrades an unrecognised compound rather than throwing", () => {
    const frame = resolvePersonalFrame(personalFrameRow({ visual_tyre_compound: 99 }));
    expect(frame.visual_tyre_compound).toBe("UNKNOWN_99");
  });
});

describe("car damage NULLs", () => {
  it("keeps withheld wear as null rather than collapsing to 0", () => {
    const damage = carDamageRow({ tyres_wear_rl: null });
    expect(damage.tyres_wear_rl).toBeNull();
    expect(damage.tyres_wear_rr).not.toBeNull();
  });
});

describe("readPersonalDamage", () => {
  it("returns null when the driver's damage row is withheld or not yet seen", async () => {
    expect(await readPersonalDamage(async () => [])).toBeNull();
  });

  it("returns the row when one exists", async () => {
    const row = carDamageRow();
    expect(await readPersonalDamage(async () => [row])).toEqual(row);
  });
});
