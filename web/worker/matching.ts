/**
 * Fuzzy driver-name matching, used to suggest which live-session driver a
 * signed-in Discord user is. Port of `f1-24-telemetry`'s
 * `code/api/app/utils/driver_matching.py`, with the trigram tier moved out of
 * Postgres and into the Worker — the candidate set is only the drivers in the
 * live session (<=22), so a database round trip buys nothing.
 */

// Longest-first: the alternation is first-match-wins, so "reserve" must be tried
// before "res" or "namereserve" normalises to "nameerve".
const KNOWN_SUFFIXES = ["wildcard", "reserve", "res", "sub", "wc"];
const SUFFIX_RE = new RegExp(`[\\s_-]+(${KNOWN_SUFFIXES.join("|")})\\s*$`, "i");

export function normalizeDriverName(name: string): string {
  const base = name
    .trim()
    .toLowerCase()
    .replace(SUFFIX_RE, "")
    .replace(/[_\-\s]+/g, "");
  const stripped = base.replace(/\d+$/, "");
  return stripped || base;
}

function bigrams(s: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (let i = 0; i < s.length - 1; i++) {
    const bigram = s.slice(i, i + 2);
    counts.set(bigram, (counts.get(bigram) ?? 0) + 1);
  }
  return counts;
}

/** Sorensen-Dice coefficient over character bigrams, 0..1. */
export function similarity(a: string, b: string): number {
  if (a === b) return 1;
  const bigramsA = bigrams(a);
  const bigramsB = bigrams(b);
  const totalA = [...bigramsA.values()].reduce((n, c) => n + c, 0);
  const totalB = [...bigramsB.values()].reduce((n, c) => n + c, 0);
  if (totalA === 0 || totalB === 0) return 0;

  let overlap = 0;
  for (const [bigram, countA] of bigramsA) {
    const countB = bigramsB.get(bigram);
    if (countB) overlap += Math.min(countA, countB);
  }
  return (2 * overlap) / (totalA + totalB);
}

/** Minimum score to consider a candidate a real match at all. */
const MIN_SCORE = 0.6;
/** Minimum lead over the runner-up — stops two lookalike names from coin-flipping. */
const MIN_MARGIN = 0.15;

export interface MatchCandidate {
  userId: number;
  driverName: string;
}

export interface MatchResult {
  userId: number;
  driverName: string;
}

/**
 * Scores every candidate against both the viewer's Discord handle and their
 * server nickname (the better of the two counts), and returns the confident
 * winner or null. "Confident" requires both a high absolute score and a clear
 * margin over the runner-up — anything short of that yields no suggestion
 * rather than a guess, since roughly 50 guild members chase 22 seats.
 */
export function matchDriver(
  viewerUsername: string,
  viewerNickname: string | null,
  candidates: MatchCandidate[]
): MatchResult | null {
  if (candidates.length === 0) return null;

  const normalizedUsername = normalizeDriverName(viewerUsername);
  const normalizedNickname = viewerNickname ? normalizeDriverName(viewerNickname) : null;

  const scored = candidates.map((candidate) => {
    const normalizedDriver = normalizeDriverName(candidate.driverName);
    const usernameScore = similarity(normalizedDriver, normalizedUsername);
    const nicknameScore = normalizedNickname
      ? similarity(normalizedDriver, normalizedNickname)
      : 0;
    return { candidate, score: Math.max(usernameScore, nicknameScore) };
  });

  scored.sort((a, b) => b.score - a.score);
  const [best, runnerUp] = scored;

  if (best.score >= 1) {
    return { userId: best.candidate.userId, driverName: best.candidate.driverName };
  }

  if (best.score < MIN_SCORE) return null;
  const margin = best.score - (runnerUp?.score ?? 0);
  if (margin < MIN_MARGIN) return null;

  return { userId: best.candidate.userId, driverName: best.candidate.driverName };
}
