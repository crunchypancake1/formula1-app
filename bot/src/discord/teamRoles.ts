/**
 * Guild roles the bot manages: one per F1 26 team plus Reserve. `key` matches
 * `telemetry.teams.name` for the `_26` team_ids (476-486) with that suffix
 * stripped, so future features can join a roster's team_name straight to a
 * role id via the map `discord/roleStore.ts` keeps in KV.
 *
 * Colors are each team's well-known livery color. Audi and Cadillac are new
 * to the 2026 grid with no confirmed official livery yet at the time this was
 * written — their colors here are provisional placeholders (Audi red, a dark
 * Cadillac navy) and worth revisiting once liveries are announced.
 */
export interface TeamRoleDef {
  key: string;
  name: string;
  color: number;
}

export const TEAM_ROLES: TeamRoleDef[] = [
  { key: "MERCEDES", name: "Mercedes", color: 0x00d2be },
  { key: "FERRARI", name: "Ferrari", color: 0xe8002d },
  { key: "RED_BULL_RACING", name: "Red Bull Racing", color: 0x4781d7 },
  { key: "WILLIAMS", name: "Williams", color: 0x64c4ff },
  { key: "ASTON_MARTIN", name: "Aston Martin", color: 0x229971 },
  { key: "ALPINE", name: "Alpine", color: 0xff87bc },
  { key: "RB", name: "RB", color: 0x6692ff },
  { key: "HAAS", name: "Haas", color: 0xb6babd },
  { key: "MCLAREN", name: "McLaren", color: 0xff8000 },
  { key: "AUDI", name: "Audi", color: 0xbb0a30 },
  { key: "CADILLAC", name: "Cadillac", color: 0x0a2f5c },
  { key: "RESERVE", name: "Reserve", color: 0x99aab5 },
];
