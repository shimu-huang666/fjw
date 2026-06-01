from __future__ import annotations

import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "光电测试技术 第3版 (范志刚，张旺，陈守谦，李洪玉编著) (z-library.sk, 1lib.sk, z-lib.sk).pdf"


def main() -> None:
    doc = fitz.open(PDF)
    if len(sys.argv) >= 4 and sys.argv[1] == "contact":
        start = int(sys.argv[2])
        end = int(sys.argv[3])
        thumbs: list[Image.Image] = []
        for page_no in range(start, end + 1):
            pix = doc[page_no - 1].get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            canvas = Image.new("RGB", (img.width, img.height + 30), "white")
            canvas.paste(img, (0, 30))
            draw = ImageDraw.Draw(canvas)
            draw.text((8, 8), f"PDF {page_no}", fill="red")
            thumbs.append(canvas)
        cols = 4
        rows = (len(thumbs) + cols - 1) // cols
        w = max(t.width for t in thumbs)
        h = max(t.height for t in thumbs)
        sheet = Image.new("RGB", (cols * w, rows * h), "white")
        for i, thumb in enumerate(thumbs):
            sheet.paste(thumb, ((i % cols) * w, (i // cols) * h))
        out = ROOT / f"_tmp_textbook_contact_{start}_{end}.jpg"
        sheet.save(out, quality=90)
        print(out)
        return

    if len(sys.argv) >= 3 and sys.argv[1] == "render":
        for arg in sys.argv[2:]:
            page_no = int(arg)
            pix = doc[page_no - 1].get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            out = ROOT / f"_tmp_textbook_page_{page_no:03d}.jpg"
            pix.save(out)
            print(out)
        return

    if len(sys.argv) >= 3 and sys.argv[1] == "pages":
        for arg in sys.argv[2:]:
            page_no = int(arg)
            text = doc[page_no - 1].get_text("text").replace("\n", " | ")
            print(f"--- PDF page {page_no} ---")
            print(text[:2500])
        return

    terms = sys.argv[1:] or [
        "435.8",
        "透射比",
        "彩度或饱和度",
        "三原色",
        "CIE1931",
        "积分透射比",
        "时间相干性",
        "光学多普勒",
        "相位测距",
        "脉冲测距",
        "电光调制",
        "锁相放大",
    ]
    for term in terms:
        hits: list[int] = []
        for i, page in enumerate(doc, start=1):
            if term in page.get_text("text"):
                hits.append(i)
        print(f"{term}: {hits[:30]}")


if __name__ == "__main__":
    main()
