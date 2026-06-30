#!/usr/bin/env python3
"""Thin stdlib client for the Apify REST API.

Runs an Actor synchronously and returns its dataset items. No third-party deps —
stdlib urllib only, to match the project's tools/ standard. The API key is read from
the repo-root .env (APIFY_API_KEY) or the environment, never hard-coded.

Apify endpoint used:
  POST /v2/acts/<actor>/run-sync-get-dataset-items
  — runs the actor, waits, and returns the dataset items inline (no polling).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_BASE = "https://api.apify.com/v2"
ROOT = Path(__file__).resolve().parents[1]


def load_env_key(name: str = "APIFY_API_KEY") -> str | None:
    """Return `name` from the process env, else parse it out of repo-root .env.

    .env is intentionally git-ignored (public repo) — we never print the value."""
    if os.environ.get(name):
        return os.environ[name]
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name:
            return v.strip().strip('"').strip("'")
    return None


class ApifyError(RuntimeError):
    pass


def run_actor(
    actor: str,
    run_input: dict,
    token: str | None = None,
    timeout: int = 300,
) -> list[dict]:
    """Run `actor` (e.g. "practicaltools~apify-google-news-scraper") with `run_input`
    and return the resulting dataset items. Raises ApifyError on HTTP / auth failure."""
    token = token or load_env_key()
    if not token:
        raise ApifyError("No APIFY_API_KEY in environment or repo-root .env")

    actor = actor.replace("/", "~")
    url = f"{API_BASE}/acts/{urllib.parse.quote(actor)}/run-sync-get-dataset-items"
    body = json.dumps(run_input).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise ApifyError(f"Apify HTTP {exc.code} for {actor}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ApifyError(f"Apify request failed for {actor}: {exc.reason}") from exc

    try:
        items = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ApifyError(f"Apify returned non-JSON for {actor}: {payload[:200]}") from exc
    if not isinstance(items, list):
        raise ApifyError(f"Expected a dataset array from {actor}, got {type(items).__name__}")
    return items
