"""Download the pinned source files into data/raw/ and verify SHA-256 (`make data`)."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, cast

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifest.yaml"
RAW = ROOT / "data" / "raw"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
    tmp.replace(dest)


def main() -> int:
    manifest = cast(dict[str, Any], yaml.safe_load(MANIFEST.read_text(encoding="utf-8")))
    sources = cast(dict[str, dict[str, str]], manifest["sources"])
    RAW.mkdir(parents=True, exist_ok=True)
    pinned_now = False
    failed = False
    for key, src in sources.items():
        dest = RAW / src["file"]
        if not dest.exists():
            print(f"download {key} ({src['version']})")
            download(src["url"], dest)
        digest = sha256_of(dest)
        if not src.get("sha256"):
            src["sha256"] = digest
            pinned_now = True
            print(f"pinned   {key} sha256={digest[:12]}…")
        elif digest != src["sha256"]:
            print(f"MISMATCH {key}: expected {src['sha256'][:12]}… got {digest[:12]}…")
            failed = True
        else:
            print(f"ok       {key} {digest[:12]}…")
    if pinned_now:
        MANIFEST.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
