"""README hero GIF from three Playwright captures of the recorded Kabir journey (replay mode).

Capture: `HERO=<dir> E2E_BASE_URL=http://127.0.0.1:8080 pnpm --dir web e2e hero`, then
`uv run python scripts/make_hero_gif.py <dir>`. Frames are stitched with Pillow (no screen recorder).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1000, 640
BG = (245, 243, 238)


def fit(im: Image.Image, w: int, h: int) -> Image.Image:
    im = im.convert("RGB")
    k = min(1.0, w / im.width)  # never blow a small capture up
    im = im.resize((round(im.width * k), round(im.height * k)), Image.Resampling.LANCZOS)
    return im.crop((0, 0, im.width, min(h, im.height)))


def label(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    d.text(xy, text, fill=(36, 48, 94), font=ImageFont.load_default(size=20))


def frame(panels: list[tuple[str, Image.Image]]) -> Image.Image:
    pw = (W - 20 * (len(panels) + 1)) // len(panels)
    fitted = [fit(im, pw, H - 50) for _, im in panels]
    canvas = Image.new("RGB", (W, H), BG)  # every frame has the same size (GIF requirement)
    d = ImageDraw.Draw(canvas)
    for i, ((title, _), im) in enumerate(zip(panels, fitted, strict=True)):
        x = 20 + i * (pw + 20)
        label(d, (x, 10), title)
        canvas.paste(im, (x, 44))
    return canvas.quantize(colors=128)


def main(src: Path) -> None:
    parent = Image.open(src / "parent.png")
    clin = Image.open(src / "clinician.png")
    head, q = (
        Image.open(src / "inspector-head.png").convert("RGB"),
        Image.open(src / "inspector-q.png").convert("RGB"),
    )
    insp = Image.new("RGB", (head.width, head.height + q.height + 10), BG)
    insp.paste(head, (0, 0))
    insp.paste(q, (0, head.height + 10))
    frames = [
        (frame([("Parent view: plain questions, no disease names", parent)]), 3500),
        (
            frame(
                [
                    ("Parent view (same family)", parent),
                    ("Clinician view: candidates + explanation paths", clin),
                ]
            ),
            6500,
        ),
        (frame([("FalkorDB inspector: the Cypher this round ran (rows, ms)", insp)]), 6500),
    ]
    out = ROOT / "docs" / "media" / "hero.gif"
    frames[0][0].save(
        out,
        save_all=True,
        append_images=[f for f, _ in frames[1:]],
        duration=[d for _, d in frames],
        loop=0,
        optimize=True,
    )
    print(
        f"wrote {out} ({out.stat().st_size // 1024} KB, {sum(d for _, d in frames) / 1000:.0f} s)"
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
