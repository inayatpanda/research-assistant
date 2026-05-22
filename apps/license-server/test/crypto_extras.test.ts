// Fix-13 regression tests for crypto helpers:
//   - constant-time string compare (admin-token gate) does not leak via
//     early bail-out on length mismatch
//   - HMAC verifier rejects non-hex signatures, length mismatches and
//     case-different signatures consistently

import { describe, it, expect } from "vitest";
import {
  timingSafeEqualString,
  verifyHmacSha256,
} from "../src/lib/crypto";

describe("timingSafeEqualString (Fix-13/2)", () => {
  it("returns true for equal strings", () => {
    expect(timingSafeEqualString("hunter2-secret", "hunter2-secret")).toBe(true);
  });

  it("returns false for mismatched strings of equal length", () => {
    expect(timingSafeEqualString("aaaaaaaa", "aaaaaaab")).toBe(false);
  });

  it("returns false for inputs of different length without leaking via short-circuit", () => {
    expect(timingSafeEqualString("short", "much-longer-token")).toBe(false);
    expect(timingSafeEqualString("much-longer-token", "short")).toBe(false);
  });

  it("returns false for empty vs non-empty", () => {
    expect(timingSafeEqualString("", "x")).toBe(false);
    expect(timingSafeEqualString("x", "")).toBe(false);
  });

  it("returns true for both-empty (degenerate)", () => {
    expect(timingSafeEqualString("", "")).toBe(true);
  });
});

async function makeSig(secret: string, body: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  return [...new Uint8Array(mac)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

describe("verifyHmacSha256 (Fix-13/3)", () => {
  it("accepts a correct signature", async () => {
    const sig = await makeSig("s", "payload");
    expect(await verifyHmacSha256("s", "payload", sig)).toBe(true);
  });

  it("rejects a wrong signature of correct length", async () => {
    const sig = "0".repeat(64);
    expect(await verifyHmacSha256("s", "payload", sig)).toBe(false);
  });

  it("rejects a signature of the wrong length", async () => {
    expect(await verifyHmacSha256("s", "payload", "abcd")).toBe(false);
  });

  it("rejects a signature containing non-hex characters", async () => {
    const real = await makeSig("s", "payload");
    // Mutate the last byte into something non-hex.
    const tampered = real.slice(0, -1) + "Z";
    expect(await verifyHmacSha256("s", "payload", tampered)).toBe(false);
  });

  it("rejects an empty signature", async () => {
    expect(await verifyHmacSha256("s", "payload", "")).toBe(false);
  });

  it("accepts an uppercase-hex signature (case-insensitive)", async () => {
    const real = await makeSig("s", "payload");
    expect(await verifyHmacSha256("s", "payload", real.toUpperCase())).toBe(true);
  });
});
