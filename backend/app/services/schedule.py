"""课表解析与对比服务。

内部统一为 CourseSlot；支持 ICS / ZJUT TXT 解析（PDF 占位），以及空闲时间对比。
解析任务应异步执行，本模块提供纯函数与规则，便于测试。
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


# ---------- 文件解析 ----------

class ScheduleParseError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def parse_schedule(data: bytes, filename: str) -> dict:
    """根据文件名识别格式并解析为 CourseSlot 列表。

    返回 {"slots": [...], "format": "ics"|"txt"}。
    """
    name = filename.lower()
    if name.endswith(".ics"):
        return {"slots": [s.to_dict() for s in parse_ics(data)], "format": "ics"}
    if name.endswith(".txt"):
        return {"slots": [s.to_dict() for s in parse_txt(data)], "format": "txt"}
    if name.endswith(".pdf"):
        raise ScheduleParseError(
            "PDF_UNSUPPORTED",
            "PDF 课表解析尚未实现，请改用 ICS 或 TXT 导出格式",
        )
    raise ScheduleParseError(
        "UNSUPPORTED_FORMAT", "仅支持 .ics / .txt 文件（PDF 暂未支持）"
    )


def parse_ics(data: bytes) -> list[CourseSlot]:
    """解析 ICS 课表：每个 VEVENT 映射为一个 CourseSlot。

    约定：重复规则每周一次（FREQ=WEEKLY）映射为周次 + weekday；
    不支持复杂 recur 的 event 按单次出现解析。
    """
    from icalendar import Calendar

    try:
        cal = Calendar.from_ical(data)
    except Exception as exc:
        raise ScheduleParseError("ICS_PARSE_FAILED", f"ICS 解析失败: {exc}") from exc

    slots: list[CourseSlot] = []
    for component in cal.walk("VEVENT"):
        summary = str(component.get("SUMMARY", ""))
        location = str(component.get("LOCATION", ""))
        dtstart = component.get("DTSTART")
        dtend = component.get("DTEND")
        rrule = component.get("RRULE")

        if dtstart is None:
            continue
        start = dtstart.dt
        end = dtend.dt if dtend is not None else start

        # weekday: 0=周一
        weekday = start.weekday()

        # 节次：按时间近似映射到 1-12 节（假设 8:00 起，每节 45min + 10min 休息）
        lesson_start = _time_to_lesson(start)
        lesson_end = _time_to_lesson(end, is_end=True)

        # 周次：从 RRULE 或单次日期推导（简化：单次事件用当周，重复事件用 UNTIL/COUNT）
        weeks = _extract_weeks(component, start)

        slots.append(
            CourseSlot(
                name=summary or "未命名课程",
                location=location,
                weekday=weekday,
                lesson_start=lesson_start,
                lesson_end=lesson_end,
                weeks=weeks,
            )
        )
    return slots


def _time_to_lesson(dt, is_end: bool = False) -> int:
    """把时间映射到节次（近似：8:00 第一节，每 55 分钟一节）。"""
    if not hasattr(dt, "hour"):
        return 1
    minutes = dt.hour * 60 + dt.minute
    start_min = 8 * 60
    if is_end:
        # 结束时间：减 1 分钟再映射，避免边界
        minutes -= 1
    lesson = (minutes - start_min) // 55 + 1
    return max(1, min(12, lesson))


def _extract_weeks(component, start) -> list[int]:
    """提取周次列表（简化实现）。"""
    rrule = component.get("RRULE")
    if rrule is not None:
        rule = {k.upper(): v for k, v in dict(rrule).items()}
        freq = rule.get("FREQ", [])[0] if rule.get("FREQ") else "WEEKLY"
        # COUNT：重复次数 → 连续周
        count = rule.get("COUNT")
        if count:
            return list(range(1, int(count[0]) + 1))
        until = rule.get("UNTIL")
        if until and freq == "WEEKLY":
            # 按 UNTIL 估算周数
            try:
                n = int((until[0] - start.date()).days / 7) + 1
                return list(range(1, n + 1))
            except Exception:
                pass
        # 默认单周
        return [1]
    # 无 RRULE：单次事件，用日期所在周（简化：第 1 周）
    return [1]


def parse_txt(data: bytes) -> list[CourseSlot]:
    """解析 ZJUT TXT 课表。

    示例格式（每行一门课，制表符或空格分隔星期与单元格内容）：
    <星期> <单元格内容>
    单元格内容格式：课程名★ (3-5节)1-11周/校区:下沙校区/场地:2-N130/教师:xxx
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("gbk")
        except UnicodeDecodeError as exc:
            raise ScheduleParseError("TXT_DECODE_FAILED", "无法识别文件编码") from exc

    slots: list[CourseSlot] = []
    weekday_map = {
        "周一": 0, "星期二": 1, "周三": 2, "星期四": 3, "周五": 4, "周六": 5, "周日": 6,
        "星期一": 0, "周二": 1, "星期二": 1, "周三": 2, "星期三": 2,
        "周四": 3, "星期四": 3, "周五": 4, "星期五": 4, "周六": 5, "星期六": 5,
        "星期日": 6, "星期天": 6, "周天": 6,
    }

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 尝试按星期前缀解析：如 "周一\t课程名★..."
        weekday = None
        cell = line
        for key, val in weekday_map.items():
            if line.startswith(key):
                weekday = val
                cell = line[len(key):].strip(" \t:：")
                break
        if weekday is None:
            # 无星期前缀，尝试按 tab 分割（第一列是星期索引 0-6）
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].strip().isdigit():
                idx = int(parts[0].strip())
                if 0 <= idx <= 6:
                    weekday = idx
                    cell = parts[1].strip()

        if weekday is None:
            continue

        parsed = parse_zjut_cell(cell, weekday)
        slots.extend(parsed)

    if not slots:
        raise ScheduleParseError("TXT_NO_COURSE", "未从文件中解析出课程，请检查格式")
    return slots