"""浙江理工大学教务课表 PDF 解析。

版式约定（教务系统打印/导出）：
- 横向表格：时间段、节次、星期一…星期日共 9 列；
- 单元格文本：`课程名★` + 换行 + `(起-止节)起-止周/校区:…/场地:…/教师:…`；
- 同一格可能有多门课；节次合并导致不能依赖表格行号，节次以 `(A-B节)` 为准；
- 打印分页时，第 2 页可能只有 10–12 节的课程详情，课程名在上一页末尾，
  需要按星期列把名称与详情拼接；
- 页眉姓名/学号、页脚“实践课程/其他课程”不属于周课表，解析时丢弃。

只做文本层表格解析，不处理扫描件（需要 OCR 的情况返回明确错误）。
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Iterable

import pdfplumber

from app.services.schedule import CourseSlot, parse_weeks

MAX_PDF_PAGES = 5
MAX_PDF_BYTES = 10 * 1024 * 1024

_DAY_LABELS = {
    "星期一": 0,
    "星期二": 1,
    "星期三": 2,
    "星期四": 3,
    "星期五": 4,
    "星期六": 5,
    "星期日": 6,
    "星期天": 6,
}
_DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
_DETAIL_RE = re.compile(r"\((\d+)(?:-(\d+))?节\)")
_TERM_RE = re.compile(r"(\d{4})\s*[-—–]\s*(\d{4})\s*学年\s*第\s*([12])\s*学期")
_CAMPUS_RE = re.compile(r"校区[:：]\s*([^/]+)")
_LOCATION_RE = re.compile(r"场地[:：]\s*([^/]+)")
_METADATA_PREFIXES = (
    "校区",
    "场地",
    "教师",
    "教学班",
    "考核",
    "选课",
    "课程",
    "周学时",
    "总学时",
    "学分",
)


class PdfParseError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class PdfParseResult:
    slots: list[CourseSlot] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_name: str = "PDF 导入课表"


def _normalize(text: str | None) -> str:
    return (text or "").replace("\r", "").replace("\u00a0", " ")


def _clean_name(value: str) -> str:
    return re.sub(r"[★○●]+\s*$", "", value).strip()


def _is_name_line(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 80:
        return False
    if ":" in line or "：" in line or "/" in line:
        return False
    if line.startswith(_METADATA_PREFIXES):
        return False
    # 课程名可能带 (应化)、II、2 等，不能把任何括号都当作元数据。
    return True


def _parse_cell_blocks(
    cell: str,
    weekday: int,
    pending_names: dict[int, list[str]],
    warnings: list[str],
) -> list[CourseSlot]:
    """解析一个单元格；可能包含多门课或仅课程名（跨页续接）。"""
    text = _normalize(cell).strip()
    if not text:
        return []
    lines = [line.strip() for line in text.split("\n")]
    detail_indices = [index for index, line in enumerate(lines) if _DETAIL_RE.search(line)]

    if not detail_indices:
        # 只有课程名的单元格：先入队，等下一页的详情行拼接。
        for line in reversed(lines):
            if _is_name_line(line):
                pending_names.setdefault(weekday, []).append(_clean_name(line))
                break
        return []

    slots: list[CourseSlot] = []
    for position, line_index in enumerate(detail_indices):
        detail_line = lines[line_index]
        match = _DETAIL_RE.search(detail_line)
        if not match:
            continue
        end_index = detail_indices[position + 1] if position + 1 < len(detail_indices) else len(lines)
        prefix = detail_line[: match.start()].strip()
        name = _clean_name(prefix)
        if not name:
            for previous in range(line_index - 1, -1, -1):
                candidate = lines[previous]
                if not candidate:
                    continue
                if _is_name_line(candidate):
                    name = _clean_name(candidate)
                break
        if not name:
            queue = pending_names.get(weekday) or []
            if queue:
                name = queue.pop(0)
        if not name:
            warnings.append(f"{_DAY_NAMES[weekday]} 有一条课程详情缺少课程名，已跳过")
            continue

        metadata = "".join(
            part.strip() for part in [detail_line[match.end() :], *lines[line_index + 1 : end_index]]
        )
        weeks = parse_weeks(metadata)
        if not weeks:
            warnings.append(f"{name} 未识别到周次，已跳过")
            continue
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        campus_match = _CAMPUS_RE.search(metadata)
        location_match = _LOCATION_RE.search(metadata)
        slots.append(
            CourseSlot(
                name=name,
                location=location_match.group(1).strip() if location_match else "",
                weekday=weekday,
                lesson_start=start,
                lesson_end=end,
                weeks=weeks,
                campus=campus_match.group(1).strip() if campus_match else None,
            )
        )
    return slots


def _day_columns(header_row: Iterable[str | None]) -> dict[int, int]:
    columns: dict[int, int] = {}
    for index, cell in enumerate(header_row):
        text = _normalize(cell).replace(" ", "")
        for label, weekday in _DAY_LABELS.items():
            if label in text:
                columns[index] = weekday
                break
    return columns


def _pick_table(page: pdfplumber.page.Page) -> list[list[str | None]] | None:
    tables = page.extract_tables()
    if not tables:
        return None
    # 最大的表格才是课表（页脚/标题偶尔会形成小表）。
    return max(tables, key=lambda table: sum(1 for row in table for cell in row if cell))


def _parse_page(
    page: pdfplumber.page.Page,
    columns: dict[int, int] | None,
    pending_names: dict[int, list[str]],
    warnings: list[str],
) -> tuple[list[CourseSlot], dict[int, int] | None]:
    table = _pick_table(page)
    if table is None:
        return [], columns

    active_columns = columns
    header_index = -1
    for row_index, row in enumerate(table[:4]):
        candidate = _day_columns(row)
        if len(candidate) >= 5:
            active_columns = candidate
            header_index = row_index
            break
    if not active_columns:
        return [], None

    slots: list[CourseSlot] = []
    start_row = header_index + 1 if header_index >= 0 else 0
    for row in table[start_row:]:
        for column_index, weekday in active_columns.items():
            if column_index >= len(row):
                continue
            slots.extend(_parse_cell_blocks(row[column_index], weekday, pending_names, warnings))
    return slots, active_columns


def parse_pdf_schedule(data: bytes) -> PdfParseResult:
    """解析 PDF 课表；失败抛 PdfParseError。"""
    if not data:
        raise PdfParseError("PDF_EMPTY", "PDF 文件为空")
    if len(data) > MAX_PDF_BYTES:
        raise PdfParseError("PDF_TOO_LARGE", "PDF 文件不能超过 10 MB")
    if not data.startswith(b"%PDF-"):
        raise PdfParseError("PDF_INVALID", "文件不是有效的 PDF")

    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:  # pdfminer/pdfplumber 的异常类型不稳定
        raise PdfParseError("PDF_INVALID", "PDF 无法打开或已损坏") from exc

    with pdf:
        if len(pdf.pages) > MAX_PDF_PAGES:
            raise PdfParseError("PDF_TOO_MANY_PAGES", f"PDF 最多支持 {MAX_PDF_PAGES} 页")
        warnings: list[str] = []
        pending_names: dict[int, list[str]] = {}
        columns: dict[int, int] | None = None
        slots: list[CourseSlot] = []
        text = ""
        for page in pdf.pages:
            page_text = _normalize(page.extract_text())
            text += page_text + "\n"
            page_slots, columns = _parse_page(page, columns, pending_names, warnings)
            slots.extend(page_slots)
            if columns is None and page_text.strip():
                raise PdfParseError(
                    "PDF_LAYOUT_UNSUPPORTED",
                    "未识别出课表表格，请使用 ICS / TXT 导出格式",
                )

        if not text.strip():
            raise PdfParseError(
                "PDF_NO_TEXT",
                "未检测到文字层，可能是扫描件；请使用 ICS / TXT 或图片版另行处理",
            )

        leftover = sum(len(queue) for queue in pending_names.values())
        if leftover:
            warnings.append(f"有 {leftover} 门课程只有名称、没有时间安排，已忽略")

        if not slots:
            raise PdfParseError(
                "PDF_NO_COURSE",
                "未从 PDF 中识别出课程，请检查是否为教务课表或改用 ICS / TXT",
            )

        # 同一 PDF 偶尔会把同一块文本重复抽取；保持确定顺序并去重。
        unique: dict[tuple, CourseSlot] = {}
        for slot in slots:
            key = (
                slot.name,
                slot.weekday,
                slot.lesson_start,
                slot.lesson_end,
                tuple(slot.weeks),
                slot.location,
                slot.campus,
            )
            unique.setdefault(key, slot)
        ordered = sorted(
            unique.values(),
            key=lambda slot: (slot.weekday, slot.lesson_start, slot.lesson_end, slot.name),
        )

        suggested_name = "PDF 导入课表"
        term_match = _TERM_RE.search(text)
        if term_match:
            suggested_name = f"{term_match.group(1)}-{term_match.group(2)}-{term_match.group(3)} 课表"

        return PdfParseResult(slots=ordered, warnings=warnings, suggested_name=suggested_name)
