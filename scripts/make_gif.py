"""Stitch the P4 screenshots into docs/media/demo.gif (README section 2). Pillow only."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "explain" / "P4-screens"
FRAMES = [
    "01-landing",
    "02-start-example",
    "03-round",
    "04-journey",
    "06-pack",
    "07-clinician",
    "09-demo-judge",
    "10-urgent",
]
WIDTH = 880


def main() -> None:
    imgs: list[Image.Image] = []
    for name in FRAMES:
        im = Image.open(SHOTS / f"{name}-1280.png").convert("RGB")
        h = round(im.height * WIDTH / im.width)
        imgs.append(im.resize((WIDTH, min(h, 620)), Image.Resampling.LANCZOS).quantize(colors=96))
    out = ROOT / "docs" / "media" / "demo.gif"
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=2400, loop=0, optimize=True)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(imgs)} frames)")


if __name__ == "__main__":
    main()
