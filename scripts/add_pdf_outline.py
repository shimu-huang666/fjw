from pathlib import Path
import re

import fitz


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_DIR = ROOT / "markdown_output_high_fidelity"
OUTPUT_DIR = ROOT / "pdf_with_outline"
COMBINED_OUTPUT = ROOT / "光电检测技术课件_带大纲.pdf"
CLEAN_OUTPUT_DIR = ROOT / "pdf_with_outline_clean"
CLEAN_COMBINED_OUTPUT = ROOT / "光电检测技术课件_简洁大纲.pdf"


def compact_title(value: str, fallback: str) -> str:
    title = re.sub(r"\s+", " ", value).strip()
    title = title.strip("`*_ ")
    return title or fallback


def parse_markdown(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    chapter_match = re.search(r"^#\s+(.+)$", text, re.M)
    source_match = re.search(r"源文件：`([^`]+)`", text)
    page_titles = [
        (int(page), compact_title(title, f"第 {page} 页"))
        for page, title in re.findall(
            r"^- \[第 (\d+) 页：(.+?)\]\(#第-\d+-页\)$", text, re.M
        )
    ]

    if not chapter_match or not source_match:
        raise ValueError(f"无法解析 {md_path.name}")

    return {
        "chapter": compact_title(chapter_match.group(1), md_path.stem),
        "source": ROOT / source_match.group(1),
        "pages": page_titles,
    }


def build_single_pdf_outline(item: dict) -> list[list[int | str]]:
    toc = [[1, item["chapter"], 1]]
    toc.extend([2, title, page] for page, title in item["pages"])
    return toc


def write_single_with_outline(item: dict) -> Path:
    source = item["source"]
    output = OUTPUT_DIR / f"{source.stem}_带大纲.pdf"

    doc = fitz.open(source)
    if len(item["pages"]) != doc.page_count:
        raise ValueError(
            f"{source.name} 页数不匹配：PDF {doc.page_count} 页，Markdown {len(item['pages'])} 页"
        )
    doc.set_toc(build_single_pdf_outline(item))
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output


def write_combined_with_outline(items: list[dict]) -> Path:
    combined = fitz.open()
    toc = []
    page_offset = 0

    for item in items:
        source = item["source"]
        doc = fitz.open(source)
        if len(item["pages"]) != doc.page_count:
            raise ValueError(
                f"{source.name} 页数不匹配：PDF {doc.page_count} 页，Markdown {len(item['pages'])} 页"
            )

        combined.insert_pdf(doc)
        toc.append([1, item["chapter"], page_offset + 1])
        toc.extend([2, title, page_offset + page] for page, title in item["pages"])
        page_offset += doc.page_count
        doc.close()

    combined.set_toc(toc)
    combined.save(COMBINED_OUTPUT, garbage=4, deflate=True)
    combined.close()
    return COMBINED_OUTPUT


def write_single_with_clean_outline(item: dict) -> Path:
    source = item["source"]
    output = CLEAN_OUTPUT_DIR / f"{source.stem}_简洁大纲.pdf"

    doc = fitz.open(source)
    doc.set_toc([[1, item["chapter"], 1]])
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    return output


def write_combined_with_clean_outline(items: list[dict]) -> Path:
    combined = fitz.open()
    toc = []
    page_offset = 0

    for item in items:
        source = item["source"]
        doc = fitz.open(source)
        combined.insert_pdf(doc)
        toc.append([1, item["chapter"], page_offset + 1])
        page_offset += doc.page_count
        doc.close()

    combined.set_toc(toc)
    combined.save(CLEAN_COMBINED_OUTPUT, garbage=4, deflate=True)
    combined.close()
    return CLEAN_COMBINED_OUTPUT


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    CLEAN_OUTPUT_DIR.mkdir(exist_ok=True)
    items = [
        parse_markdown(path)
        for path in sorted(MARKDOWN_DIR.glob("*.md"))
        if path.name.lower() != "readme.md"
    ]

    single_outputs = [write_single_with_clean_outline(item) for item in items]
    combined_output = write_combined_with_clean_outline(items)

    print(f"combined\t{combined_output}")
    for output in single_outputs:
        print(f"single\t{output}")


if __name__ == "__main__":
    main()
