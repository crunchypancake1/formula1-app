import { describe, it, expect } from "vitest";
import {
  finalCardFor,
  placeholderCard,
  practiceCard,
  qualifyingCard,
  raceCard,
} from "../../src/discord/cards";
import { qualifyingResult, raceResult, sessionBest, sessionRow, trackRow } from "../fixtures";

describe("placeholderCard", () => {
  it("shows a countdown for a non-race session when given a target timestamp", () => {
    const card = placeholderCard(
      sessionRow({ session_type: "QUALIFYING_1" }),
      trackRow(),
      1755000000
    );
    expect(card).toContain("<t:1755000000:R>");
    expect(card).toContain("Session live…");
  });

  it("never shows a countdown for a race session", () => {
    const card = placeholderCard(sessionRow({ session_type: "RACE" }), trackRow(), null);
    expect(card).not.toContain("<t:");
    expect(card).toContain("In progress…");
  });
});

describe("practiceCard", () => {
  it("orders drivers by best lap time, fastest first", () => {
    const bests = [
      sessionBest({ user_id: 2, driver_name: "Slower", best_lap_time_ms: 90000 }),
      sessionBest({ user_id: 1, driver_name: "Faster", best_lap_time_ms: 85000 }),
    ];
    const card = practiceCard(sessionRow({ session_type: "PRACTICE_1" }), trackRow(), bests);
    expect(card.indexOf("Faster")).toBeLessThan(card.indexOf("Slower"));
  });

  it("reports no laps set instead of an empty table", () => {
    const card = practiceCard(sessionRow({ session_type: "PRACTICE_1" }), trackRow(), []);
    expect(card).toContain("No laps set yet.");
  });
});

describe("qualifyingCard", () => {
  it("inserts the cutoff line at the elimination boundary for Q1", () => {
    const results = Array.from({ length: 18 }, (_, i) =>
      qualifyingResult({ position: i + 1, driver_name: `Driver ${i + 1}` })
    );
    const card = qualifyingCard(
      sessionRow({ session_type: "QUALIFYING_1" }),
      trackRow(),
      results
    );
    expect(card).toContain("CUTOFF — TOP 16 ADVANCE");
    expect(card.indexOf("Driver 16")).toBeLessThan(card.indexOf("CUTOFF"));
    expect(card.indexOf("CUTOFF")).toBeLessThan(card.indexOf("Driver 17"));
  });

  it("omits the cutoff line for Q3, which has no elimination", () => {
    const results = [qualifyingResult({ position: 1 })];
    const card = qualifyingCard(
      sessionRow({ session_type: "QUALIFYING_3" }),
      trackRow(),
      results
    );
    expect(card).not.toContain("CUTOFF");
  });
});

describe("raceCard", () => {
  it("splits finishers from DNFs and shows the reason for each DNF", () => {
    const results = [
      raceResult({ position: 1, driver_name: "Winner", result_status: "FINISHED" }),
      raceResult({
        position: 0,
        driver_name: "Retired Driver",
        result_status: "RETIRED",
        result_reason: "MECHANICAL_FAILURE",
      }),
    ];
    const card = raceCard(sessionRow({ session_type: "RACE" }), trackRow(), results);
    expect(card).toContain("Winner");
    expect(card).toContain("DNF / DSQ");
    expect(card).toContain("Retired Driver — Mechanical Failure");
  });

  it("shows the race leader's absolute time and gaps for the rest", () => {
    const results = [
      raceResult({ position: 1, driver_name: "Leader", total_race_time: 5400 }),
      raceResult({ position: 2, driver_name: "Chaser", total_race_time: 5410.5 }),
    ];
    const card = raceCard(sessionRow({ session_type: "RACE" }), trackRow(), results);
    expect(card).toContain("+10.500");
  });
});

describe("finalCardFor", () => {
  it("dispatches races to raceCard", () => {
    const session = sessionRow({ session_type: "RACE" });
    const card = finalCardFor(session, trackRow(), { race: [raceResult()] });
    expect(card).not.toContain("No classified result yet.");
  });

  it("dispatches qualifying and sprint shootout sessions to qualifyingCard", () => {
    const session = sessionRow({ session_type: "SPRINT_SHOOTOUT_1" });
    const card = finalCardFor(session, trackRow(), { qualifying: [qualifyingResult()] });
    expect(card).toContain("Best Lap");
  });

  it("dispatches everything else to practiceCard", () => {
    const session = sessionRow({ session_type: "PRACTICE_2" });
    const card = finalCardFor(session, trackRow(), { bests: [sessionBest()] });
    expect(card).toContain("S1");
  });
});
