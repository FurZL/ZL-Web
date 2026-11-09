"""课表解析与对比服务。

内部统一为 CourseSlot；支持 ICS / ZJUT PDF/TXT 解析，以及多人空闲时间对比。
解析任务应异步执行，本模块只提供纯函数与规则，便于测试。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass
class CourseSlot:
    name: str
    location: str
    weekday: int  # 0=周一 … 6=周日
    lesson_start: int  # 开始节次（1-12）
    lesson_end: int  # 结束节次
    weeks: list[int]  # [1, 2, 3, ...]
    campus: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ZJUT 课表示例单元格：
# 课程名★ (3-5节)1-11周/校区:下沙校区/场地:2-N130/教师:xxx/...
_LESSON_RE = re.compile(r"\((\d+)-(\d+)节\)")
_WEEKS_RE = re.compile(r"(\d+)-(\d+)周")
_SINGLE_WEEKS_RE = re.compile(r"(\d+(?:,\d+)*)周")
_CAMPUS_RE = re.compile(r"校区[:：]([^/]+)")
_LOCATION_RE = re.compile(r"场地[:：]([^/]+)")


def parse_weeks(text: str) -> list[int]:
    """解析周次：`1-16周` 连续；`1,3,5周` 指定周。"""
    if "-" in text:
        m = _WEEKS_RE.search(text)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start <= end:
                return list(range(start, end + 1))
    m = _SINGLE_WEEKS_RE.search(text)
    if m:
        return [int(w) for w in m.group(1).split(",")]
    return []


def parse_zjut_cell(cell: str, weekday: int) -> list[CourseSlot]:
    """解析单个 ZJUT 课表单元格，可能含多门课程（以换行或分隔符分开）。"""
    slots: list[CourseSlot] = []
    for part in re.split(r"[\n;；]", cell):
        part = part.strip()
        if not part:
            continue
        name = re.split(r"★|\(", part)[0].strip()
        lesson = _LESSON_RE.search(part)
        weeks = parse_weeks(part)
        campus_m = _CAMPUS_RE.search(part)
        campus = campus_m.group(1).strip() if campus_m else None
        location_m = _LOCATION_RE.search(part)
        location = location_m.group(1).strip() if location_m else ""
        if not lesson or not weeks:
            continue
        slots.append(
            CourseSlot(
                name=name or "未命名课程",
                location=location or "",
                weekday=weekday,
                lesson_start=int(lesson.group(1)),
                lesson_end=int(lesson.group(2)),
                weeks=weeks,
                campus=campus,
            )
        )
    return slots


def _weeks_overlap(a: list[int], b: list[int]) -> bool:
    return bool(set(a) & set(b))


def compare(slots_a: list[CourseSlot], slots_b: list[CourseSlot]) -> dict:
    """对比两份课表。

    返回：
      same_classroom: 同教室同时间（考虑周次交集）
      both_free:      A 与 B 都空闲的时段
      overlaps:       行课时段冲突（周次真正重叠才算）
    """
    same_classroom: list[dict] = []
    both_free: list[dict] = []
    overlaps: list[dict] = []

    for a in slots_a:
        for b in slots_b:
            if a.weekday != b.weekday:
                continue
            if not _weeks_overlap(a.weeks, b.weeks):
                continue
            # 节次有交叠
            if max(a.lesson_start, b.lesson_start) <= min(a.lesson_end, b.lesson_end):
                if a.location and a.location == b.location:
                    same_classroom.append(
                        {"a": a.to_dict(), "b": b.to_dict(), "weekday": a.weekday}
                    )
                else:
                    overlaps.append(
                        {"a": a.to_dict(), "b": b.to_dict(), "weekday": a.weekday}
                    )

    # 空闲时段：一周内所有非行课时段（简化：以课表覆盖的周次、按天/节次求差集）
    free = _free_slots(slots_a, slots_b)
    both_free = free
    return {
        "same_classroom": same_classroom,
        "both_free": both_free,
        "overlaps": overlaps,
    }


_DAYS = 7
_MAX_LESSON = 12


def _occupied_intervals(slots: list[CourseSlot], weekday: int) -> list[tuple[int, int]]:
    return [
        (s.lesson_start, s.lesson_end)
        for s in slots
        if s.weekday == weekday
    ]


def _free_slots(slots_a: list[CourseSlot], slots_b: list[CourseSlot]) -> list[dict]:
    """返回 A、B 都空闲的时间段（按天、按连续节次）。"""
    result: list[dict] = []
    for day in range(_DAYS):
        occupied = sorted(
            _occupied_intervals(slots_a, day) + _occupied_intervals(slots_b, day)
        )
        merged: list[tuple[int, int]] = []
        for s, e in occupied:
            if merged and s <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        free_intervals: list[tuple[int, int]] = []
        cursor = 1
        for s, e in merged:
            if cursor <= s - 1:
                free_intervals.append((cursor, s - 1))
            cursor = max(cursor, e + 1)
        if cursor <= _MAX_LESSON:
            free_intervals.append((cursor, _MAX_LESSON))
        for s, e in free_intervals:
            result.append(
                {"weekday": day, "lesson_start": s, "lesson_end": e}
            )
    return result