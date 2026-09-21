"""Visual sanity check: each query photo next to its Top-5 catalog references.

Calls the running web API (/v1/search), so it exercises the full pipeline.

Usage: python ml/scripts/contact_sheet.py --dir eval/queries [--url http://127.0.0.1:8080]
Output: reports/contact_sheet.jpg
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import urllib.request
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

CELL = 220
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"}


def search(url: str, path: Path) -> dict:
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{url}/v1/search", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def thumb(path: Path) -> Image.Image:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.getchannel("A"))
    return ImageOps.pad(bg, (CELL, CELL), color="white")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=Path("eval/queries"))
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    ap.add_argument("--out", type=Path, default=Path("reports/contact_sheet.jpg"))
    args = ap.parse_args()

    wines = {json.loads(l)["slug"]: json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")}
    queries = sorted(p for p in args.dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    sheet = Image.new("RGB", (CELL * 6, (CELL + 60) * len(queries)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()

    for row, q in enumerate(queries):
        res = search(args.url, q)
        y = row * (CELL + 60)
        sheet.paste(thumb(q), (0, y))
        draw.text((4, y + CELL + 4), f"{q.name}\n{res['latency_ms']} ms, margin {res['margin']}", fill="black", font=font)
        for col, c in enumerate(res["top5"], start=1):
            sheet.paste(thumb(args.catalog / "images" / wines[c["slug"]]["image_file"]), (col * CELL, y))
            draw.text((col * CELL + 4, y + CELL + 4), f"#{col} {c['score']:.3f}\n{c['name'][:28]}\n{c['slug'][:30]}",
                      fill="black", font=font)
        print(q.name, "->", [(c["slug"], c["score"]) for c in res["top5"]])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out, quality=88)
    print("saved", args.out)


if __name__ == "__main__":
    main()
