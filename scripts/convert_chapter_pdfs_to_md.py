from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "markdown_output_high_fidelity"
ASSETS = OUTPUT / "assets"


@dataclass(frozen=True)
class ChapterFile:
    order: int
    path: Path
    title: str
    slug: str


CHAPTERS = [
    ChapterFile(1, ROOT / "第一章 绪论2026 - Copy.pdf", "第一章 绪论", "01_第一章_绪论"),
    ChapterFile(2, ROOT / "第二章 光电检测中常用的光源.pdf", "第二章 光电检测中常用的光源", "02_第二章_光电检测中常用的光源"),
    ChapterFile(3, ROOT / "第三章 色度和光度测试技术.pdf", "第三章 色度和光度测试技术", "03_第三章_色度和光度测试技术"),
    ChapterFile(4, ROOT / "第四章-1 光信号调制（精简）.pdf", "第四章-1 光信号调制（精简）", "04_第四章-1_光信号调制"),
    ChapterFile(5, ROOT / "第四章-3 光学时间分辨测量技术-1.pdf", "第四章-3 光学时间分辨测量技术", "05_第四章-3_光学时间分辨测量技术"),
    ChapterFile(6, ROOT / "第五章 激光测试技术.pdf", "第五章 激光测试技术", "06_第五章_激光测试技术"),
    ChapterFile(7, ROOT / "第六章 激光干涉测试技术.pdf", "第六章 激光干涉测试技术", "07_第六章_激光干涉测试技术"),
    ChapterFile(8, ROOT / "第七章 激光衍射测试技术.pdf", "第七章 激光衍射测试技术", "08_第七章_激光衍射测试技术"),
    ChapterFile(9, ROOT / "第八章 莫尔测试技术.pdf", "第八章 莫尔测试技术", "09_第八章_莫尔测试技术"),
]


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def render_page(page: fitz.Page, target: Path) -> None:
    # 1.5x keeps slide details readable without producing huge assets.
    matrix = fitz.Matrix(1.5, 1.5)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    pix.save(str(target), jpg_quality=82)


def page_title(text: str, fallback: str) -> str:
    for line in clean_text(text).splitlines():
        line = line.strip()
        if 4 <= len(line) <= 60 and not re.fullmatch(r"\d+", line):
            return line
    return fallback


def convert_chapter(chapter: ChapterFile) -> dict[str, object]:
    if not chapter.path.exists():
        return {
            "title": chapter.title,
            "slug": chapter.slug,
            "exists": False,
            "pages": 0,
            "chars": 0,
        }

    asset_dir = ASSETS / chapter.slug
    asset_dir.mkdir(parents=True, exist_ok=True)
    md_path = OUTPUT / f"{chapter.slug}.md"

    doc = fitz.open(chapter.path)
    pages: list[dict[str, object]] = []
    lines: list[str] = [
        f"# {chapter.title}",
        "",
        f"- 源文件：`{chapter.path.name}`",
        f"- 页数：{doc.page_count}",
        "- 转换方式：每页保留原始页面截图，并提取 PDF 文本层作为可检索内容。",
        "- 说明：公式、复杂图形、版式细节以页面截图为准；文字区用于搜索和快速复习。",
        "",
        "## 页面索引",
        "",
    ]

    for idx, page in enumerate(doc, start=1):
        text = clean_text(page.get_text("text", sort=True))
        title = page_title(text, f"第 {idx} 页")
        image_name = f"page-{idx:03d}.jpg"
        image_path = asset_dir / image_name
        render_page(page, image_path)
        pages.append({"index": idx, "title": title, "chars": len(text)})
        anchor = f"第-{idx}-页"
        lines.append(f"- [第 {idx} 页：{title}](#{anchor})")

    lines.append("")

    for item in pages:
        idx = int(item["index"])
        page = doc[idx - 1]
        text = clean_text(page.get_text("text", sort=True))
        image_rel = f"assets/{chapter.slug}/page-{idx:03d}.jpg"
        title = str(item["title"])
        lines.extend(
            [
                f"## 第 {idx} 页",
                "",
                f"**页面标题/首行：** {title}",
                "",
                f"![{chapter.title} 第 {idx} 页]({image_rel})",
                "",
                "### 本页文字",
                "",
            ]
        )
        if text:
            lines.extend(["```text", text, "```", ""])
        else:
            lines.extend(["> 本页未检测到可提取文本，请以页面截图为准。", ""])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    total_chars = sum(int(item["chars"]) for item in pages)
    return {
        "title": chapter.title,
        "slug": chapter.slug,
        "exists": True,
        "pages": doc.page_count,
        "chars": total_chars,
        "md": md_path,
    }


def write_index(results: list[dict[str, object]]) -> None:
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_pages = sum(int(r["pages"]) for r in results if r["exists"])
    total_chars = sum(int(r["chars"]) for r in results if r["exists"])
    lines = [
        "# 光电检测技术课件 Markdown 索引",
        "",
        f"- 生成时间：{generated}",
        f"- 已转换文件数：{sum(1 for r in results if r['exists'])}",
        f"- 合计页数：{total_pages}",
        f"- 合计可检索字符数：{total_chars}",
        "- 范围：第一章至第八章课件 PDF。",
        "",
        "## 文件清单",
        "",
        "| 序号 | Markdown | 页数 | 可检索字符数 |",
        "|---:|---|---:|---:|",
    ]
    for idx, result in enumerate(results, start=1):
        if result["exists"]:
            md_name = f"{result['slug']}.md"
            lines.append(
                f"| {idx} | [{result['title']}]({md_name}) | {result['pages']} | {result['chars']} |"
            )
        else:
            lines.append(f"| {idx} | {result['title']}（源文件缺失） | 0 | 0 |")

    lines.extend(
        [
            "",
            "## 完整性说明",
            "",
            "- 当前目录没有发现 PPT/PPTX 源文件，转换依据为同目录下章节 PDF。",
            "- 当前可用章节 PDF 为 9 个：第一、二、三、四章-1、四章-3、五、六、七、八章。",
            "- 未发现“第四章-2”或可对应“第十个 PPT”的源文件；如后续补充源文件，可继续追加转换。",
            "- 每个 Markdown 页面包含原始页面截图和文本层提取结果；截图用于版式还原，文本用于搜索。",
            "",
        ]
    )
    (OUTPUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    ASSETS.mkdir(exist_ok=True)
    results = [convert_chapter(chapter) for chapter in CHAPTERS]
    write_index(results)


if __name__ == "__main__":
    main()
