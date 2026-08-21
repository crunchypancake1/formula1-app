import { describe, it, expect, beforeAll } from "vitest";
import { verifyDiscordRequest, verifyRequestHeaders } from "../../src/discord/verify";

/**
 * Signs with a real Ed25519 keypair generated inside the Workers runtime
 * rather than a fixed vector — that way the test also proves workerd's
 * WebCrypto accepts the `Ed25519` algorithm name the source uses, which is the
 * part most likely to break the endpoint in production.
 */
function toHex(buffer: ArrayBuffer): string {
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

let publicKeyHex: string;
let sign: (message: string) => Promise<string>;

beforeAll(async () => {
  const pair = (await crypto.subtle.generateKey({ name: "Ed25519" }, true, [
    "sign",
    "verify",
  ])) as CryptoKeyPair;

  publicKeyHex = toHex(
    (await crypto.subtle.exportKey("raw", pair.publicKey)) as ArrayBuffer
  );
  sign = async (msg) =>
    toHex(await crypto.subtle.sign("Ed25519", pair.privateKey, new TextEncoder().encode(msg)));
});

const TIMESTAMP = "1755781200";
const BODY = JSON.stringify({ type: 1 });

describe("verifyDiscordRequest", () => {
  it("accepts a correctly signed body", async () => {
    const signature = await sign(TIMESTAMP + BODY);
    expect(await verifyDiscordRequest(publicKeyHex, signature, TIMESTAMP, BODY)).toBe(true);
  });

  it("rejects a body that changed after signing", async () => {
    const signature = await sign(TIMESTAMP + BODY);
    const tampered = JSON.stringify({ type: 2 });
    expect(await verifyDiscordRequest(publicKeyHex, signature, TIMESTAMP, tampered)).toBe(false);
  });

  it("rejects a replay under a different timestamp", async () => {
    const signature = await sign(TIMESTAMP + BODY);
    expect(await verifyDiscordRequest(publicKeyHex, signature, "1755781999", BODY)).toBe(false);
  });

  it("rejects a signature from the wrong key", async () => {
    const other = (await crypto.subtle.generateKey({ name: "Ed25519" }, true, [
      "sign",
      "verify",
    ])) as CryptoKeyPair;
    const signature = toHex(
      await crypto.subtle.sign("Ed25519", other.privateKey, new TextEncoder().encode(TIMESTAMP + BODY))
    );
    expect(await verifyDiscordRequest(publicKeyHex, signature, TIMESTAMP, BODY)).toBe(false);
  });

  it("rejects malformed input instead of throwing", async () => {
    const signature = await sign(TIMESTAMP + BODY);
    expect(await verifyDiscordRequest(publicKeyHex, "nothex", TIMESTAMP, BODY)).toBe(false);
    expect(await verifyDiscordRequest(publicKeyHex, "abc", TIMESTAMP, BODY)).toBe(false);
    expect(await verifyDiscordRequest("zz", signature, TIMESTAMP, BODY)).toBe(false);
    expect(await verifyDiscordRequest(publicKeyHex, undefined, TIMESTAMP, BODY)).toBe(false);
    expect(await verifyDiscordRequest(publicKeyHex, signature, undefined, BODY)).toBe(false);
    expect(await verifyDiscordRequest("", signature, TIMESTAMP, BODY)).toBe(false);
  });

  it("reads both headers off a request", async () => {
    const signature = await sign(TIMESTAMP + BODY);
    const headers = new Headers({
      "x-signature-ed25519": signature,
      "x-signature-timestamp": TIMESTAMP,
    });
    expect(await verifyRequestHeaders(publicKeyHex, headers, BODY)).toBe(true);
    expect(await verifyRequestHeaders(publicKeyHex, new Headers(), BODY)).toBe(false);
  });
});
