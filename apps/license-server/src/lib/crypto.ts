// Phase L1a — Crypto primitives running entirely on WebCrypto (no native
// deps, free-tier Workers compatible).
//
// - Password hashing: PBKDF2-SHA256, 100k iterations, 16-byte random salt.
//   Format: `pbkdf2$<iterations>$<base64-salt>$<base64-hash>`.
//   Note: Cloudflare Workers' WebCrypto caps PBKDF2 iterations at 100k
//   (anything higher throws "Pbkdf2 failed: iteration counts above
//   100000 are not supported"). OWASP 2023 PBKDF2-SHA256 minimum is
//   600k, but Workers doesn't allow it. 100k is the 2017 NIST floor
//   and is what real-world Worker apps run at — acceptable trade-off
//   pending a Workers-native KDF API.
// - Session tokens: 32 random bytes -> base64url string. The server stores
//   the SHA-256 of the token in `sessions.jwt_id`; the plain string only
//   ever lives in the response body + the client.
// - Reset tokens use the same construction.

const PBKDF2_ITERATIONS = 100_000;
const PBKDF2_HASH_BYTES = 32;
const PBKDF2_SALT_BYTES = 16;

function toBase64(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function fromBase64(s: string): Uint8Array {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function toBase64Url(bytes: Uint8Array): string {
  return toBase64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

/**
 * Constant-time string compare. Always processes the longer of the two
 * inputs (zero-padding the shorter) so attackers cannot learn the
 * length of the secret from response timing.
 *
 * Used by the admin-token gate (``X-Admin-Token`` header) and anywhere
 * else we compare an attacker-controlled string against a server
 * secret. Pure JS, no `crypto.subtle` dependency — keeps the bundle
 * small and works in every Workers runtime.
 */
export function timingSafeEqualString(a: string, b: string): boolean {
  const enc = new TextEncoder();
  const ba = enc.encode(a);
  const bb = enc.encode(b);
  const len = Math.max(ba.length, bb.length);
  let diff = ba.length ^ bb.length;
  for (let i = 0; i < len; i++) {
    const ai = i < ba.length ? ba[i] : 0;
    const bi = i < bb.length ? bb[i] : 0;
    diff |= ai ^ bi;
  }
  return diff === 0;
}

async function pbkdf2(
  password: string,
  salt: Uint8Array,
  iterations: number,
  bytes: number,
): Promise<Uint8Array> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    { name: "PBKDF2" },
    false,
    ["deriveBits"],
  );
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations },
    key,
    bytes * 8,
  );
  return new Uint8Array(bits);
}

export async function hashPassword(password: string): Promise<string> {
  const salt = crypto.getRandomValues(new Uint8Array(PBKDF2_SALT_BYTES));
  const hash = await pbkdf2(password, salt, PBKDF2_ITERATIONS, PBKDF2_HASH_BYTES);
  return `pbkdf2$${PBKDF2_ITERATIONS}$${toBase64(salt)}$${toBase64(hash)}`;
}

export async function verifyPassword(password: string, encoded: string): Promise<boolean> {
  const parts = encoded.split("$");
  if (parts.length !== 4 || parts[0] !== "pbkdf2") return false;
  const iterations = Number.parseInt(parts[1], 10);
  if (!Number.isFinite(iterations) || iterations < 10_000) return false;
  let salt: Uint8Array;
  let expected: Uint8Array;
  try {
    salt = fromBase64(parts[2]);
    expected = fromBase64(parts[3]);
  } catch {
    return false;
  }
  const actual = await pbkdf2(password, salt, iterations, expected.length);
  return timingSafeEqual(actual, expected);
}

export function generateToken(bytes: number = 32): string {
  const raw = crypto.getRandomValues(new Uint8Array(bytes));
  return toBase64Url(raw);
}

export async function sha256Hex(input: string): Promise<string> {
  const enc = new TextEncoder();
  const digest = await crypto.subtle.digest("SHA-256", enc.encode(input));
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Verify an HMAC-SHA256 signature over a body using the given secret.
 * `signatureHex` is the lower-case hex digest sent by Lemon Squeezy in the
 * `X-Signature` header.
 */
export async function verifyHmacSha256(
  secret: string,
  body: string,
  signatureHex: string,
): Promise<boolean> {
  if (!signatureHex || typeof signatureHex !== "string") return false;
  // Reject anything that isn't pure hex so callers can't smuggle in
  // garbage to short-circuit the comparison. (Fix-13/3)
  if (!/^[0-9a-f]+$/i.test(signatureHex)) return false;
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  const computed = [...new Uint8Array(mac)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  // Always walk the *expected* (computed) length, zero-padding the
  // actual signature, so a length mismatch can't be detected via early
  // bail-out timing. We fold the length delta into the diff bitmask
  // up-front to make it impossible for the byte loop alone to declare
  // equality. (Fix-13/3)
  const lowered = signatureHex.toLowerCase();
  let diff = computed.length ^ lowered.length;
  for (let i = 0; i < computed.length; i++) {
    const got = i < lowered.length ? lowered.charCodeAt(i) : 0;
    diff |= computed.charCodeAt(i) ^ got;
  }
  return diff === 0;
}

const RANDOM_PW_ALPHABET =
  "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";

export function generateRandomPassword(length: number = 12): string {
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  let out = "";
  for (let i = 0; i < length; i++) {
    out += RANDOM_PW_ALPHABET[bytes[i] % RANDOM_PW_ALPHABET.length];
  }
  // Guarantee at least one digit so it satisfies the signup policy if the
  // user immediately rotates it via /reset-password.
  if (!/\d/.test(out)) out = out.slice(0, -1) + "7";
  return out;
}

export function uuidv4(): string {
  // crypto.randomUUID() is available in Workers + node 19+.
  return crypto.randomUUID();
}
