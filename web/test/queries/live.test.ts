import { describe, it, expect } from "vitest";
import type { LiveDriverRow } from "@f1/db";
import { resolveLiveDriver } from "../../worker/queries/live";

/**
 * telemetry.car_frame stores enum columns as the game's raw integer, so the
 * dashboard only ever sees a name because this function put it there. These
 * pin the mapping the schema's SMALLINT columns are written against.
 */
function row(overrides: Partial<LiveDriverRow> = {}): LiveDriverRow {
  return {
    user_id: 1,
    car_index: 0,
    driver_name: "Driver One",
    team_name: "MCLAREN_26",
    team_display_name: "McLaren '26",
    race_number: 4,

    position: 1,
    current_lap_num: 12,
    sector: 0,
    lap_distance: 1234.5,
    total_distance: 56789,

    last_lap_time_ms: 83456,
    current_lap_time_ms: 21000,
    sector1_time_ms: 28000,
    sector2_time_ms: 30000,

    gap_to_leader_ms: 0,
    gap_to_car_ahead_ms: 0,

    pit_status: 0,
    driver_status: 4,
    result_status: 2,
    current_lap_invalid: false,

    actual_tyre_compound: 20,
    visual_tyre_compound: 16,
    tyres_age_laps: 5,

    num_pit_stops: 1,
    penalties_seconds: 0,
    total_warnings: 0,
    speed: 312,

    overtake_active: false,
    best_lap_time_ms: 83456,
    ...overrides,
  };
}

describe("resolveLiveDriver", () => {
  it("resolves every enum code to the member name the dashboard renders", () => {
    const d = resolveLiveDriver(row());

    expect(d.sector).toBe("SECTOR_1");
    expect(d.pit_status).toBe("NONE");
    expect(d.driver_status).toBe("ON_TRACK");
    expect(d.result_status).toBe("ACTIVE");
    expect(d.actual_tyre_compound).toBe("C1");
    expect(d.visual_tyre_compound).toBe("SOFT");
  });

  it("leaves the non-enum columns untouched", () => {
    const d = resolveLiveDriver(row());

    expect(d.driver_name).toBe("Driver One");
    expect(d.last_lap_time_ms).toBe(83456);
    expect(d.speed).toBe(312);
    expect(d.current_lap_invalid).toBe(false);
  });

  it("keeps a code of 0 distinct from a withheld NULL", () => {
    // PitStatus 0 is NONE — a real reading. NULL means the game did not send it.
    expect(resolveLiveDriver(row({ pit_status: 0 })).pit_status).toBe("NONE");
    expect(resolveLiveDriver(row({ pit_status: null })).pit_status).toBeNull();
  });

  it("degrades a compound a game patch added rather than dropping the driver", () => {
    const d = resolveLiveDriver(row({ visual_tyre_compound: 99 }));

    expect(d.visual_tyre_compound).toBe("UNKNOWN_99");
    expect(d.driver_name).toBe("Driver One");
  });

  it("renders the pit and retirement states the leaderboard badges key off", () => {
    expect(resolveLiveDriver(row({ pit_status: 1 })).pit_status).toBe("PITTING");
    expect(resolveLiveDriver(row({ pit_status: 2 })).pit_status).toBe("IN_PIT_AREA");
    expect(resolveLiveDriver(row({ driver_status: 3 })).driver_status).toBe("OUT_LAP");
    expect(resolveLiveDriver(row({ result_status: 7 })).result_status).toBe("RETIRED");
    expect(resolveLiveDriver(row({ result_status: 5 })).result_status).toBe("DISQUALIFIED");
  });
});
