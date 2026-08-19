import { describe, it, expect } from "vitest";
import { buildFeed } from "../../worker/queries/feed";
import type {
  FastestLapEventRow,
  PenaltyEventRow,
  RaceControlEventRow,
  RetirementEventRow,
} from "@f1/db";

function rc(overrides: Partial<RaceControlEventRow> = {}): RaceControlEventRow {
  return {
    overall_frame_identifier: 100,
    session_time: 10,
    event_code: "LGOT",
    safety_car_type: null,
    safety_car_event_type: null,
    num_lights: null,
    drs_disabled_reason: null,
    ...overrides,
  };
}

function penalty(overrides: Partial<PenaltyEventRow> = {}): PenaltyEventRow {
  return {
    overall_frame_identifier: 200,
    session_time: 20,
    driver_name: "Driver One",
    other_driver_name: null,
    penalty_type: "TIME_PENALTY",
    infringement_type: "CORNER_CUTTING_GAINED_TIME",
    time_seconds: 5,
    lap_num: 3,
    places_gained: 0,
    ...overrides,
  };
}

function retirement(overrides: Partial<RetirementEventRow> = {}): RetirementEventRow {
  return {
    overall_frame_identifier: 300,
    session_time: 30,
    driver_name: "Driver Two",
    reason: "MECHANICAL_FAILURE",
    ...overrides,
  };
}

function fastestLap(overrides: Partial<FastestLapEventRow> = {}): FastestLapEventRow {
  return {
    overall_frame_identifier: 400,
    session_time: 40,
    driver_name: "Driver Three",
    lap_time: 83.456,
    ...overrides,
  };
}

describe("buildFeed", () => {
  it("orders every source by overall_frame_identifier, most recent first", () => {
    const feed = buildFeed(
      [rc({ overall_frame_identifier: 100 })],
      [penalty({ overall_frame_identifier: 200 })],
      [retirement({ overall_frame_identifier: 300 })],
      [fastestLap({ overall_frame_identifier: 400 })]
    );

    expect(feed.map((item) => item.frame)).toEqual([400, 300, 200, 100]);
  });

  it("renders a penalty with a time_seconds value as an 'Ns time penalty'", () => {
    const [item] = buildFeed([], [penalty({ time_seconds: 5 })], [], []);

    expect(item.message).toBe(
      "5s time penalty — Driver One (Corner Cutting Gained Time)"
    );
    expect(item.kind).toBe("penalty");
  });

  it("falls back to the penalty type when there is no time value (e.g. a warning)", () => {
    const [item] = buildFeed(
      [],
      [penalty({ time_seconds: null, penalty_type: "WARNING" })],
      [],
      []
    );

    expect(item.message).toBe("Warning — Driver One (Corner Cutting Gained Time)");
  });

  it("names the other driver for a penalty involving two cars", () => {
    const [item] = buildFeed(
      [],
      [penalty({ other_driver_name: "Driver Two", infringement_type: "BIG_COLLISION" })],
      [],
      []
    );

    expect(item.message).toContain("involving Driver Two");
  });

  it("formats a fastest-lap event's seconds as m:ss.mmm, not raw seconds", () => {
    const [item] = buildFeed([], [], [], [fastestLap({ lap_time: 83.456 })]);

    expect(item.message).toBe("Driver Three sets fastest lap — 1:23.456");
  });

  it("renders a retirement with a humanized reason", () => {
    const [item] = buildFeed([], [], [retirement({ reason: "TERMINAL_DAMAGE" })], []);

    expect(item.message).toBe("Driver Two has retired — Terminal Damage");
  });

  it("builds a safety car message from type + event", () => {
    const [item] = buildFeed(
      [rc({ event_code: "SCAR", safety_car_type: "VIRTUAL", safety_car_event_type: "DEPLOYED" })],
      [],
      [],
      []
    );

    expect(item.message).toBe("Virtual Safety Car deployed");
    expect(item.kind).toBe("safety-car");
  });

  it("drops a SCAR event whose type is NONE rather than showing a blank line", () => {
    const feed = buildFeed(
      [rc({ event_code: "SCAR", safety_car_type: "NONE" })],
      [],
      [],
      []
    );

    expect(feed).toEqual([]);
  });

  it("includes the reason on a DRS-disabled event", () => {
    const [item] = buildFeed(
      [rc({ event_code: "DRSD", drs_disabled_reason: "SAFETY_CAR_DEPLOYED" })],
      [],
      [],
      []
    );

    expect(item.message).toBe("DRS disabled — Safety Car Deployed");
    expect(item.kind).toBe("drs");
  });

  it("caps the merged feed at 30 items even when every source is full", () => {
    const many = Array.from({ length: 40 }, (_, i) => rc({ overall_frame_identifier: i }));
    const feed = buildFeed(many, [penalty()], [retirement()], [fastestLap()]);

    expect(feed.length).toBe(30);
  });
});
