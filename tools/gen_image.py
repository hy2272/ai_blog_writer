#!/usr/bin/env python3
"""Generate an image with Google's Gemini image models (a.k.a. "Nano Banana").

This is the *production* half of the Xiaohongshu visual pipeline: it produces the
background photo / illustration files that platforms/xiaohongshu/adapter.py then
composites short text over. The two halves are decoupled on purpose — this tool only
emits image FILES; the adapter only consumes them. So a card layout never depends on how
its imagery was made (real photo, AI image, or CSS placeholder).

Deliberately stdlib-only (urllib + base64 + json), matching the adapter's no-dependency
stance and dodging wheel-availability risk on bleeding-edge Python. No SDK required.

Auth: reads GOOGLE_API_KEY from the environment, else from the repo-root .env (which is
gitignored). The key is never logged.

Models (image-capable, via the generateContent REST endpoint):
  gemini-3-pro-image        Nano Banana Pro  — highest quality, the default (best 高级感)
  gemini-2.5-flash-image    Nano Banana      — faster / cheaper, good for drafts
  gemini-3.1-flash-image    newer flash tier

Usage:
  python3 tools/gen_image.py --prompt "..." --out path.png
  python3 tools/gen_image.py --prompt "..." --out p.png --model gemini-2.5-flash-image --aspect 16:9
  python3 tools/gen_image.py --prompt "..." --out p.png --ref a.png --ref b.png   # image-to-image
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3-pro-image"
# Aspect ratios the Gemini 3 image models accept under generationConfig.imageConfig.
VALID_ASPECTS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}


# Either name works; GEMINI_API_KEY is checked first — it is the image-gen-specific key
# (the paid-tier one), whereas a generic GOOGLE_API_KEY may belong to a free-tier project
# shared with other tools. Note the Bash tool spawns a fresh shell each call, so a key
# exported in another terminal is invisible — put it in .env.
KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def load_api_key() -> str:
    """Env first, then repo-root .env. Never printed anywhere."""
    for name in KEY_NAMES:
        val = os.environ.get(name)
        if val:
            return val.strip()
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        # Parse all candidates, then pick by KEY_NAMES PRIORITY — not by file order, so a
        # paid GEMINI_API_KEY wins over a free GOOGLE_API_KEY that happens to appear first.
        found: dict[str, str] = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, _, val = line.partition("=")
            name, val = name.strip(), val.strip().strip('"').strip("'")
            if name in KEY_NAMES and val:
                found[name] = val
        for name in KEY_NAMES:
            if name in found:
                return found[name]
    raise SystemExit(
        "ERROR: no API key (checked env + .env for GOOGLE_API_KEY / GEMINI_API_KEY). "
        "Add it to the repo-root .env (the Bash shell can't see other terminals' exports)."
    )


def _ref_part(path: Path) -> dict:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime, "data": data}}


def _post(model: str, body: dict, key: str, timeout: int) -> dict:
    url = f"{API_BASE}/{model}:generateContent?key={key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            msg = json.loads(detail).get("error", {}).get("message", detail)
        except Exception:
            msg = detail
        raise RuntimeError(f"HTTP {exc.code} from {model}: {msg[:500]}") from None


def _extract_image(resp: dict) -> tuple[bytes | None, str]:
    """Return (image_bytes, any_text). The image model may also emit a text part
    (a caption, or a refusal explaining why it produced no image) — surface it."""
    text_bits: list[str] = []
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"]), ""
            if part.get("text"):
                text_bits.append(part["text"])
    return None, " ".join(text_bits).strip()


def generate(
    prompt: str,
    out_path: Path,
    model: str = DEFAULT_MODEL,
    aspect: str | None = None,
    refs: list[Path] | None = None,
    timeout: int = 180,
) -> Path:
    key = load_api_key()
    parts: list[dict] = []
    for r in refs or []:
        parts.append(_ref_part(Path(r)))
    parts.append({"text": prompt})

    base_body = {"contents": [{"role": "user", "parts": parts}]}

    # Attempt with imageConfig.aspectRatio (Gemini 3 image). Older models reject it, so
    # retry once without on a 400. responseModalities is added on the retry too, since some
    # tiers need it spelled out to emit an image instead of text.
    attempts: list[dict] = []
    if aspect:
        cfg = {"imageConfig": {"aspectRatio": aspect}}
        attempts.append({**base_body, "generationConfig": cfg})
    attempts.append({**base_body, "generationConfig": {"responseModalities": ["IMAGE"]}})
    attempts.append(base_body)

    last_text = ""
    for i, body in enumerate(attempts):
        try:
            resp = _post(model, body, key, timeout)
        except RuntimeError as exc:
            # A 400 from the aspect/config attempt → fall through to the next variant.
            if i < len(attempts) - 1 and "HTTP 400" in str(exc):
                continue
            raise
        img, text = _extract_image(resp)
        if img:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(img)
            return out_path
        last_text = text or last_text

    hint = f" Model said: {last_text!r}" if last_text else ""
    raise RuntimeError(f"No image returned by {model}.{hint}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate an image with Gemini (Nano Banana).")
    ap.add_argument("--prompt", required=True, help="image description")
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"model id (default {DEFAULT_MODEL})")
    ap.add_argument("--aspect", help=f"aspect ratio, one of {sorted(VALID_ASPECTS)}")
    ap.add_argument("--ref", action="append", default=[],
                    help="reference image for image-to-image (repeatable)")
    ap.add_argument("--timeout", type=int, default=180, help="seconds per API call")
    args = ap.parse_args(argv)

    if args.aspect and args.aspect not in VALID_ASPECTS:
        print(f"WARN: --aspect {args.aspect} not in {sorted(VALID_ASPECTS)}; sending anyway",
              file=sys.stderr)
    try:
        out = generate(
            args.prompt, Path(args.out), model=args.model, aspect=args.aspect,
            refs=[Path(p) for p in args.ref], timeout=args.timeout,
        )
    except (RuntimeError, SystemExit) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    size = out.stat().st_size
    print(json.dumps({"out": str(out), "bytes": size, "model": args.model,
                      "aspect": args.aspect}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
