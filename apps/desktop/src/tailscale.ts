/**
 * Phase E1.4 — Tailscale detection.
 *
 * We never require Tailscale; the app runs fully locally without it. When
 * the CLI is installed we surface the tailnet URL so the user can plug it
 * into a phone or second laptop.
 *
 * Order of preference for the URL:
 *
 *   1. MagicDNS name (e.g. `your-mac.tail-abc123.ts.net`) — pretty + stable.
 *   2. IPv4 100.x.x.x — works even with MagicDNS disabled.
 *
 * All shell-outs are best-effort and time-bounded; a failure returns
 * ``null`` rather than crashing the boot path.
 */
import { exec } from "node:child_process";
import { promisify } from "node:util";

const pExec = promisify(exec);

const TAILSCALE_TIMEOUT_MS = 2_000;

async function runTailscale(args: string): Promise<string | null> {
  try {
    const { stdout } = await pExec(`tailscale ${args}`, {
      timeout: TAILSCALE_TIMEOUT_MS,
    });
    return stdout.trim() || null;
  } catch {
    return null;
  }
}

async function tailnetDnsName(): Promise<string | null> {
  const raw = await runTailscale("status --json");
  if (!raw) return null;
  try {
    const json = JSON.parse(raw) as {
      Self?: { DNSName?: string; HostName?: string };
    };
    // DNSName comes with a trailing dot — strip it.
    const dns = json.Self?.DNSName?.replace(/\.$/, "");
    if (dns && dns.length > 0) return dns;
    return null;
  } catch {
    return null;
  }
}

async function tailnetIp(): Promise<string | null> {
  const raw = await runTailscale("ip --4");
  if (!raw) return null;
  // First line is the device's IPv4 in the tailnet.
  const ip = raw.split(/\s+/)[0];
  if (!ip || !/^100\.\d+\.\d+\.\d+$/.test(ip)) return null;
  return ip;
}

/** Build a `http://<host>:<port>` URL, or null if Tailscale isn't usable. */
export async function detectTailnetUrl(port: number): Promise<string | null> {
  const dns = await tailnetDnsName();
  if (dns) return `http://${dns}:${port}`;
  const ip = await tailnetIp();
  if (ip) return `http://${ip}:${port}`;
  return null;
}
