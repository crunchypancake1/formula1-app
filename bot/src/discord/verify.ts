/**
 * Discord signs every inbound POST over `X-Signature-Timestamp || rawBody`.
 * Shared by `interactions.ts` and `events.ts`.
 */

export const SIGNATURE_HEADER = "x-signature-ed25519";
export const TIMESTAMP_HEADER = "x-signature-timestamp";

function hexToBytes(hex: string): Uint8Array | null {
  if (hex.length === 0 || hex.length % 2 !== 0 || !/^[0-9a-fA-F]+$/.test(hex)) return null;

  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = Number.parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

/** Malformed input returns false, not a throw — a garbage header is an unauthenticated request. */
export async function verifyDiscordRequest(
  publicKey: string,
  signature: string | undefined,
  timestamp: string | undefined,
  rawBody: string
): Promise<boolean> {
  if (!publicKey || !signature || !timestamp) return false;

  const keyBytes = hexToBytes(publicKey);
  const signatureBytes = hexToBytes(signature);
  if (!keyBytes || !signatureBytes) return false;

  try {
    const key = await crypto.subtle.importKey("raw", keyBytes, { name: "Ed25519" }, false, [
      "verify",
    ]);
    return await crypto.subtle.verify(
      "Ed25519",
      key,
      signatureBytes,
      new TextEncoder().encode(timestamp + rawBody)
    );
  } catch {
    return false; // a wrong-length key throws where verify would have returned false
  }
}

/** Verifies a request's signature headers against `rawBody`. */
export function verifyRequestHeaders(
  publicKey: string,
  headers: Headers,
  rawBody: string
): Promise<boolean> {
  return verifyDiscordRequest(
    publicKey,
    headers.get(SIGNATURE_HEADER) ?? undefined,
    headers.get(TIMESTAMP_HEADER) ?? undefined,
    rawBody
  );
}
