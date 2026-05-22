#!/usr/bin/env python3
"""Phase L1a — Mint a Research Assistant licence via the admin endpoint.

Use this to comp lifetime licences for reviewers, demos, or to bootstrap
a fresh deployment. Auth is via the ADMIN_TOKEN secret set on the Worker.

Examples:
  python scripts/mint_license.py \\
      --email reviewer@example.com --name "Reviewer" --type lifetime

  RMA_ADMIN_TOKEN=xxx python scripts/mint_license.py \\
      --email tester@example.com --name "Tester" --type trial \\
      --server-url https://research-assistant-license.workers.dev
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests

DEFAULT_SERVER_URL = "https://research-assistant-license.workers.dev"
DEFAULT_TIMEOUT = 30


def mint_license(
    server_url: str,
    admin_token: str,
    email: str,
    name: str,
    license_type: str,
    password: str | None = None,
    *,
    session: requests.Session | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST /api/admin/mint and return the parsed JSON response.

    Raises requests.HTTPError on non-2xx.
    """
    if license_type not in ("trial", "lifetime"):
        raise ValueError(f"license_type must be 'trial' or 'lifetime', got {license_type!r}")
    body: dict[str, Any] = {
        "email": email,
        "display_name": name,
        "type": license_type,
    }
    if password:
        body["password"] = password
    url = server_url.rstrip("/") + "/api/admin/mint"
    sess = session or requests.Session()
    resp = sess.post(
        url,
        json=body,
        headers={"X-Admin-Token": admin_token},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def _pretty_print(payload: dict[str, Any]) -> None:
    acct = payload.get("account", {})
    print("Minted licence")
    print("  id:                  ", acct.get("id"))
    print("  email:               ", acct.get("email"))
    print("  display_name:        ", acct.get("display_name"))
    print("  type:                ", acct.get("type"))
    print("  trial_expires_at:    ", acct.get("trial_expires_at"))
    print("  lifetime_purchased_at:", acct.get("lifetime_purchased_at"))
    if payload.get("temp_password"):
        print()
        print("  TEMPORARY PASSWORD (share securely, then rotate):")
        print("  ", payload["temp_password"])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mint_license",
        description="Mint a Research Assistant trial or lifetime licence.",
    )
    p.add_argument("--email", required=True, help="Buyer's email address.")
    p.add_argument("--name", required=True, help="Display name on the account.")
    p.add_argument(
        "--type",
        choices=["trial", "lifetime"],
        required=True,
        help="Licence type.",
    )
    p.add_argument(
        "--server-url",
        default=os.environ.get("RMA_LICENSE_SERVER_URL", DEFAULT_SERVER_URL),
        help=f"Licence server URL (default: {DEFAULT_SERVER_URL}).",
    )
    p.add_argument(
        "--admin-token",
        default=os.environ.get("RMA_ADMIN_TOKEN"),
        help="Admin token (default: $RMA_ADMIN_TOKEN).",
    )
    p.add_argument(
        "--password",
        default=None,
        help="Optional explicit password. If omitted, the server generates one.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON response instead of a pretty summary.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.admin_token:
        print(
            "error: --admin-token (or $RMA_ADMIN_TOKEN) is required.",
            file=sys.stderr,
        )
        return 2
    try:
        payload = mint_license(
            server_url=args.server_url,
            admin_token=args.admin_token,
            email=args.email,
            name=args.name,
            license_type=args.type,
            password=args.password,
        )
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else "<no body>"
        print(f"error: HTTP {exc.response.status_code if exc.response else '?'}: {body}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        _pretty_print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
