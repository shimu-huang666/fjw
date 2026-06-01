from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MD_DIR = ROOT / "markdown_output_high_fidelity"
REVIEW_FILE = ROOT / "课程复习（2026）.md"
OUT_FILE = ROOT / "课件题目重点筛选.md"


QUESTION_TITLE_RE = re.compile(r"^(单选题|多选题|填空题|判断题)\s*(\d+)\s*分")
PAGE_RE = re.compile(
    r"^## 第 (?P<page>\d+) 页\s*\n(?P<body>.*?)(?=^## 第 \d+ 页\s*$|\Z)",
    re.M | re.S,
)
TITLE_RE = re.compile(r"\*\*页面标题/首行：\*\*\s*(?P<title>.+)")
TEXT_RE = re.compile(r"### 本页文字\s*\n\s*```text\s*\n(?P<text>.*?)\n```", re.S)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?P<path>assets/[^)]+)\)")


STOP_LINES = {
    "提交",
    "作答",
    "正常使用填空题需3.0以上版本雨课堂",
}


@dataclass
class FocusItem:
    chapter: str
    text: str
    keywords: set[str]


@dataclass
class Question:
    chapter_file: str
    chapter_title: str
    source_pdf: str
    page: int
    qtype: str
    points: str
    image_rel: str
    stem: str
    options: dict[str, str] = field(default_factory=dict)
    answer: str = ""
    raw_text: str = ""
    matched_focus: list[str] = field(default_factory=list)
    score: int = 0
    priority: str = "待核对"


FOCUS_RULES: list[tuple[str, str, str, list[str]]] = [
    ("第一章", r"组成部分|光学变换|光电变换|电路处理", "高", ["光电检测系统的三个组成部分"]),
    ("第二章", r"光度计量|光通量|发光强度|照度|亮度", "高", ["各辐射度量和光度量的定义、关系，简单的应用计算"]),
    ("第二章", r"辐射分为|平衡辐射|非平衡辐射", "高", ["黑体的基本概念，黑体辐射的基本规律（理解）"]),
    ("第二章", r"实际物体|灰体|黑体|人工黑体", "高", ["黑体的基本概念，黑体辐射的基本规律（理解）"]),
    ("第二章", r"混合光谱|线状光谱|发射线状光谱|光源的颜色|肉眼直接看到光源", "中", ["常见光源的光谱特性分类"]),
    ("第二章", r"光强度空间分布|配光曲线", "高", ["光源的空间光强分布"]),
    ("第二章", r"THz|太赫兹", "低/拓展", ["未列入 2026 复习重点，作为课件拓展题保留"]),
    ("第三章", r"白色的加入|彩度|补色|蓝光|黄色物体|黄色色料|色料三原色|色光三原色", "高", ["颜色的基本属性、颜色混合定律", "相加混合和相减混合，色光三原色与色料三原色的关系"]),
    ("第三章", r"辐射通量相等|LED.*最亮|视觉亮度", "中", ["光度量与视觉亮度关系，属于第三章光度/色度基础题"]),
    ("第三章", r"颜色刺激函数|三刺激值|色品坐标|光谱三刺激值", "高", ["三刺激值、光谱三刺激值、色品坐标及其关系", "反射物体或透射物体的三刺激值计算方法（连续积分、离散求和）"]),
    ("第三章", r"CIE定义的标准|标准.*照明体|标准.*光源", "高", ["标准照明体和标准光源的概念（理解）"]),
    ("第三章", r"分光光度法|光谱透过率|光谱反射率", "高", ["分光光度计测色方法（结合三刺激值计算方法理解）", "反射物体或透射物体的三刺激值计算方法（连续积分、离散求和）"]),
    ("第四章", r"泵浦|探测|超短光|光学延迟线|荧光上转换|脉宽|不可逆", "高", ["时间分辨测量中探测器响应速度的影响（理解）", "泵浦-探测技术的基本原理（理解，能简单画图）"]),
    ("第四章", r"调制盘|斩波|锁相|光子计数|取样积分|采样积分|弱水三千|千呼万唤|前后关联|光功率小于", "高", ["锁相放大技术、采样积分技术和光子计数技术实现微弱信号检测的基本原理和应用特点（理解，例如：锁相如何压缩信号带宽，相敏检波的作用，采样积分利用信号前后关联性，“相对弱”与“绝对弱”问题……）"]),
    ("第四章", r"泡克尔斯|克尔效应|电光|声光|磁光|偏振方向调制", "高", ["电光调制的基本原理", "声光调制的基本原理（结合第 7 章声光光栅）", "磁光调制的基本原理"]),
    ("第五章", r"位相板|准直", "高", ["光束准直技术与激光准直测试技术的概念区别"]),
    ("第五章", r"角锥|偏移量|平行偏移|角度偏移", "高", ["两种偏移量（角度、平行）的测量方法"]),
    ("第五章", r"脉冲激光测距|分辨力|激光脉冲宽度|计数脉冲频率", "高", ["激光脉冲测距的原理（简单计算）"]),
    ("第五章", r"多普勒", "高", ["声学多普勒和光学多普勒效应的主要区别"]),
    ("第五章", r"连续调谐|可连续调谐", "低/拓展", ["未列入 2026 复习重点，作为课件拓展题保留"]),
    ("第六章", r"光程差|零级|斐索|分光方式|分振幅|分波阵面|共程|非共程", "高", ["激光斐索干涉仪的干涉类型、分类及基本应用（理解及简单计算应用）"]),
    ("第六章", r"光学计数倍频|倍频", "高", ["光学计数倍频技术（理解，能简单画图）"]),
    ("第六章", r"外差|双频|塞曼|双纵模|声光效应|旋转的波片", "高", ["激光外差干涉测试技术要解决的问题及基本原理（理解）", "获得外差干涉光源的方法（了解）"]),
    ("第六章", r"移相|最小二乘", "高", ["激光移相干涉测试技术的基本原理（了解，最小二乘法拟合）"]),
    ("第七章", r"衍射间隙|间隙测量|细丝直径|巴比涅", "高", ["单缝衍射公式再实际测量中的运用（简单计算应用）", "间隙测量法、反射衍射测量法、分离间隙法的应用场合（了解）", "巴比涅互补原理及其应用"]),
    ("第七章", r"光谱仪|光栅|分光元件", "高", ["光栅衍射的基本原理（理解，两个因子，色散本领、分辨力、自由光谱范围）", "闪耀光栅与光谱仪"]),
]


def chapter_key(s: str) -> str:
    m = re.search(r"第[一二三四五六七八九十]+章", s)
    return m.group(0) if m else ""


def norm(s: str) -> str:
    s = s.replace("\u3000", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def tokens(s: str) -> set[str]:
    words = set()
    for part in re.split(r"[，。、；：:（）()、/\s]+", s):
        part = part.strip(" -—…“”\"'[]【】")
        if len(part) >= 2 and part not in {"理解", "了解", "应用", "特点", "基本", "原理"}:
            words.add(part)
    return words


def load_focus_items() -> list[FocusItem]:
    text = REVIEW_FILE.read_text(encoding="utf-8")
    items: list[FocusItem] = []
    chapter = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## "):
            chapter = line[3:].strip()
        elif line.startswith("- "):
            item = line[2:].strip()
            items.append(FocusItem(chapter=chapter, text=item, keywords=tokens(item)))
    return items


def parse_meta(md_text: str, fallback: str) -> tuple[str, str]:
    title = fallback
    source = ""
    for line in md_text.splitlines()[:20]:
        if line.startswith("# "):
            title = line[2:].strip()
        elif "源文件：" in line:
            m = re.search(r"`([^`]+)`", line)
            source = m.group(1) if m else line.split("：", 1)[-1].strip()
    return title, source


def clean_question_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        line = norm(line)
        line = re.sub(r"\s+(提交|作答)(\s+\d+)?$", "", line).strip()
        if not line or line in STOP_LINES:
            continue
        if re.fullmatch(r"(提交|作答)(\s+\d+)?", line):
            continue
        if line.startswith("正常使用填空题需"):
            continue
        out.append(line)
    return out


def split_choice_text(lines: list[str]) -> tuple[str, dict[str, str]]:
    body = lines[1:] if lines and QUESTION_TITLE_RE.match(lines[0]) else lines[:]
    stem_lines: list[str] = []
    options: dict[str, list[str]] = {}
    current: str | None = None

    for line in body:
        start = re.match(r"^([A-E])\s+(.+)$", line)
        end = re.match(r"^(.+?)\s+([A-E])$", line)
        if start:
            current = start.group(1)
            options.setdefault(current, []).append(start.group(2).strip())
            continue
        if end and not re.match(r".*[A-Z]{2,}$", line):
            current = end.group(2)
            options.setdefault(current, []).append(end.group(1).strip())
            continue
        if current:
            options.setdefault(current, []).append(line)
        else:
            stem_lines.append(line)

    cleaned_options = {
        k: norm(" ".join(v))
        for k, v in sorted(options.items())
        if norm(" ".join(v))
    }
    return norm(" ".join(stem_lines)), cleaned_options


def split_fill_text(lines: list[str]) -> str:
    body = lines[1:] if lines and QUESTION_TITLE_RE.match(lines[0]) else lines[:]
    body = [line for line in body if "雨课堂" not in line]
    return re.sub(r"\s+(提交|作答)(\s+\d+)?$", "", norm(" ".join(body))).strip()


def detect_green_answer(image_path: Path) -> str:
    if not image_path.exists():
        return ""
    img = Image.open(image_path).convert("RGB")
    pix = img.load()
    w, h = img.size
    green_rows: list[int] = []
    for y in range(h):
        count = 0
        for x in range(max(0, int(w * 0.05)), min(w, int(w * 0.28))):
            r, g, b = pix[x, y]
            if g > 180 and r < 80 and b < 80:
                count += 1
        if count >= 20:
            green_rows.append(y)

    groups: list[tuple[int, int]] = []
    for y in green_rows:
        if not groups or y > groups[-1][1] + 1:
            groups.append((y, y))
        else:
            groups[-1] = (groups[-1][0], y)

    centers = [(a + b) / 2 for a, b in groups if b - a >= 20]
    if not centers:
        return ""

    # 选项框在截图中从上到下对应 A-E；只要检测绿色框，就能得到课件标出的答案。
    all_rows: list[int] = []
    for y in range(h):
        count = 0
        for x in range(max(0, int(w * 0.05)), min(w, int(w * 0.28))):
            r, g, b = pix[x, y]
            if abs(r - g) < 15 and abs(g - b) < 15 and 60 <= r <= 170:
                count += 1
        if count >= 20:
            all_rows.append(y)
    all_groups: list[tuple[int, int]] = []
    for y in sorted(set(all_rows + green_rows)):
        if not all_groups or y > all_groups[-1][1] + 1:
            all_groups.append((y, y))
        else:
            all_groups[-1] = (all_groups[-1][0], y)
    all_centers = [(a + b) / 2 for a, b in all_groups if b - a >= 20]
    letters = "ABCDE"
    answer = []
    for c in centers:
        nearest = min(range(len(all_centers)), key=lambda i: abs(all_centers[i] - c))
        if nearest < len(letters):
            answer.append(letters[nearest])
    return "".join(dict.fromkeys(answer))


def extract_questions() -> tuple[list[Question], list[tuple[str, str]]]:
    questions: list[Question] = []
    chapters: list[tuple[str, str]] = []
    for md_path in sorted(MD_DIR.glob("*.md")):
        if md_path.name.lower() == "readme.md":
            continue
        text = md_path.read_text(encoding="utf-8")
        chapter_title, source_pdf = parse_meta(text, md_path.stem)
        chapters.append((chapter_title, source_pdf))
        for m in PAGE_RE.finditer(text):
            page = int(m.group("page"))
            body = m.group("body")
            title_match = TITLE_RE.search(body)
            page_title = norm(title_match.group("title")) if title_match else ""
            text_match = TEXT_RE.search(body)
            raw = text_match.group("text").strip() if text_match else ""
            first_line = norm(raw.splitlines()[0]) if raw.strip() else ""
            qmatch = QUESTION_TITLE_RE.match(page_title) or QUESTION_TITLE_RE.match(first_line)
            if not qmatch:
                continue
            image_match = IMAGE_RE.search(body)
            image_rel = image_match.group("path") if image_match else ""
            lines = clean_question_lines(raw)
            qtype, points = qmatch.group(1), qmatch.group(2)
            if qtype in {"单选题", "多选题"}:
                stem, options = split_choice_text(lines)
                answer = detect_green_answer(MD_DIR / image_rel) if image_rel else ""
            else:
                stem = split_fill_text(lines)
                options = {}
                answer = ""
            questions.append(
                Question(
                    chapter_file=md_path.name,
                    chapter_title=chapter_title,
                    source_pdf=source_pdf,
                    page=page,
                    qtype=qtype,
                    points=points,
                    image_rel=str(Path("markdown_output_high_fidelity") / image_rel) if image_rel else "",
                    stem=stem,
                    options=options,
                    answer=answer,
                    raw_text=raw,
                )
            )
    return questions, chapters


def apply_focus(questions: list[Question], focus_items: list[FocusItem]) -> None:
    for q in questions:
        hay_text = " ".join([q.chapter_title, q.stem, " ".join(q.options.values())])
        hay = tokens(hay_text)
        q_chapter = chapter_key(q.chapter_title)
        scored: list[tuple[int, FocusItem]] = []
        for item in focus_items:
            if chapter_key(item.chapter) != q_chapter:
                continue
            direct_hits = sum(1 for kw in item.keywords if kw and kw in hay_text)
            overlap = len(hay & item.keywords)
            score = direct_hits * 2 + overlap
            if score >= 3:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        q.score = scored[0][0] if scored else 0
        q.matched_focus = [item.text for _, item in scored[:3]]
        if q.score >= 6:
            q.priority = "高"
        elif q.score >= 3:
            q.priority = "中"
        else:
            q.priority = "低/未命中复习重点"

        for chapter, pattern, priority, focus in FOCUS_RULES:
            if chapter_key(chapter) == q_chapter and re.search(pattern, hay_text, re.I):
                q.priority = priority
                q.matched_focus = focus
                break


def scan_pdf_question_pages(chapters: list[tuple[str, str]]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for chapter, source_pdf in chapters:
        pdf_path = ROOT / source_pdf
        pages: list[int] = []
        if pdf_path.exists():
            with fitz.open(pdf_path) as doc:
                for idx, page in enumerate(doc, start=1):
                    text = page.get_text("text")
                    if re.search(r"(单选题|多选题|填空题|判断题)\s*\d+\s*分", text):
                        pages.append(idx)
        found[chapter] = pages
    return found


def render_report(questions: list[Question], chapters: list[tuple[str, str]]) -> str:
    by_chapter: dict[str, list[Question]] = {}
    for q in questions:
        by_chapter.setdefault(q.chapter_title, []).append(q)
    pdf_pages = scan_pdf_question_pages(chapters)
    md_pages = {chapter: [q.page for q in by_chapter.get(chapter, [])] for chapter, _ in chapters}
    mismatches = [
        chapter
        for chapter, pages in pdf_pages.items()
        if pages != md_pages.get(chapter, [])
    ]

    choice_count = sum(1 for q in questions if q.qtype in {"单选题", "多选题"})
    fill_count = sum(1 for q in questions if q.qtype == "填空题")
    answer_count = sum(1 for q in questions if q.answer)

    lines: list[str] = []
    lines.append("# 课件题目重点筛选")
    lines.append("")
    lines.append("说明：本文件从 `markdown_output_high_fidelity` 的课件页块抽取题页，并用页面截图中的绿色选项框识别选择题答案；重点匹配依据 `课程复习（2026）.md`。")
    lines.append("")
    lines.append("## 完整性校验")
    lines.append("")
    lines.append(f"- 已扫描分章课件 Markdown：{len(chapters)} 个。")
    lines.append(f"- 已识别题页：{len(questions)} 页，其中选择题 {choice_count} 页，填空题 {fill_count} 页。")
    lines.append(f"- 已从截图识别出绿色答案的选择题：{answer_count}/{choice_count} 页。")
    pdf_total = sum(len(v) for v in pdf_pages.values())
    lines.append(f"- 原始分章 PDF 文本层直扫题页：{pdf_total} 页；与 Markdown 抽取结果{'一致' if not mismatches else '不一致，需核对：' + '、'.join(mismatches)}。")
    lines.append("- 判定规则：页面标题/首行为 `单选题/多选题/填空题/判断题 + 分值` 的页全部纳入。")
    lines.append("- 未计入：教材 PDF、课程复习 PDF、合订版 PDF，避免与分章课件重复。")
    lines.append("")
    lines.append("### 分章题页计数")
    lines.append("")
    lines.append("| 章节 | 题页数 | 页码 |")
    lines.append("|---|---:|---|")
    for chapter, _source_pdf in chapters:
        qs = by_chapter.get(chapter, [])
        pages = "、".join(f"{q.page}({q.qtype})" for q in qs)
        lines.append(f"| {chapter} | {len(qs)} | {pages or '无题页'} |")
    lines.append("")
    lines.append("## 按复习重点筛选")
    lines.append("")
    level_titles = {
        "高": "高重点",
        "中": "中重点",
        "低/拓展": "低/拓展题",
        "低/未命中复习重点": "低/未命中复习重点",
    }
    for level in ("高", "中", "低/拓展", "低/未命中复习重点"):
        subset = [q for q in questions if q.priority == level]
        lines.append(f"### {level_titles[level]}（{len(subset)}题）")
        lines.append("")
        for i, q in enumerate(subset, 1):
            lines.append(f"#### {i}. {q.chapter_title} 第 {q.page} 页｜{q.qtype} {q.points}分")
            lines.append("")
            lines.append(f"- 来源：`{q.source_pdf}`")
            if q.image_rel:
                lines.append(f"- 截图：`{q.image_rel}`")
            lines.append(f"- 题干：{q.stem or '（题干需看截图/原页）'}")
            if q.options:
                for letter, option in q.options.items():
                    mark = "（绿色答案）" if letter in q.answer else ""
                    lines.append(f"  - {letter}. {option}{mark}")
            if q.answer:
                lines.append(f"- 绿色答案：{q.answer}")
            if q.matched_focus:
                lines.append("- 命中复习重点：" + "；".join(q.matched_focus))
            else:
                lines.append("- 命中复习重点：未直接命中，建议低优先级浏览。")
            lines.append("")
    lines.append("## 原始题页文本备查")
    lines.append("")
    for q in questions:
        lines.append(f"### {q.chapter_title} 第 {q.page} 页")
        lines.append("")
        lines.append("```text")
        lines.append(q.raw_text)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    focus_items = load_focus_items()
    questions, chapters = extract_questions()
    apply_focus(questions, focus_items)
    OUT_FILE.write_text(render_report(questions, chapters), encoding="utf-8")
    print(f"questions={len(questions)}")
    print(f"choices={sum(1 for q in questions if q.qtype in {'单选题', '多选题'})}")
    print(f"fills={sum(1 for q in questions if q.qtype == '填空题')}")
    print(f"green_answers={sum(1 for q in questions if q.answer)}")
    print(f"output={OUT_FILE}")


if __name__ == "__main__":
    main()
