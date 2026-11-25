"""课表作息配置：节次时间生成、规范化和校验。"""

from __future__ import annotations

from datetime import date, datetime

MIN_PERIOD_COUNT = 1
MAX_PERIOD_COUNT = 24
DEFAULT_PERIOD_COUNT = 12
DEFAULT_FIRST_START = "08:00"
DEFAULT_LESSON_MINUTES = 45
DEFAULT_BREAK_MINUTES = 10
DEFAULT_SEGMENTS = {"noon": "12:00", "afternoon": "14:00", "evening": "18:00"}


def _clock_minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _clock(value: int) -> str:
    if not 0 <= value < 24 * 60:
        raise ValueError("作息时间不能超出当天 00:00–23:59")
    return f"{value // 60:02d}:{value % 60:02d}"


def build_periods(
    first_start: str = DEFAULT_FIRST_START,
    lesson_minutes: int = DEFAULT_LESSON_MINUTES,
    break_minutes: int = DEFAULT_BREAK_MINUTES,
    period_count: int = DEFAULT_PERIOD_COUNT,
) -> list[list[str]]:
    """按统一课间生成指定数量的节次；午休等特殊间隔可逐节微调。"""
    if not MIN_PERIOD_COUNT <= period_count <= MAX_PERIOD_COUNT:
        raise ValueError(f"节数应在 {MIN_PERIOD_COUNT}–{MAX_PERIOD_COUNT} 之间")
    current = _clock_minutes(first_start)
    return [
        [
            _clock(current + index * (lesson_minutes + break_minutes)),
            _clock(current + index * (lesson_minutes + break_minutes) + lesson_minutes),
        ]
        for index in range(period_count)
    ]


def default_timing(period_count: int = DEFAULT_PERIOD_COUNT) -> dict:
    return {
        "term_start": None,
        "first_start": DEFAULT_FIRST_START,
        "lesson_minutes": DEFAULT_LESSON_MINUTES,
        "break_minutes": DEFAULT_BREAK_MINUTES,
        "segments": dict(DEFAULT_SEGMENTS),
        "periods": build_periods(period_count=period_count),
    }


def normalize_timing(value: dict | None) -> dict:
    """给旧课表补齐默认配置，避免旧记录没有 timing 时前端失去时间显示。"""
    base = default_timing()
    if not value:
        return base
    result = {**base, **value}
    segments = value.get("segments")
    if isinstance(segments, dict):
        result["segments"] = {
            key: segments.get(key, default) for key, default in DEFAULT_SEGMENTS.items()
        }
    else:
        result["segments"] = dict(DEFAULT_SEGMENTS)
    periods = value.get("periods")
    if not isinstance(periods, list) or not MIN_PERIOD_COUNT <= len(periods) <= MAX_PERIOD_COUNT:
        result["periods"] = build_periods(
            result["first_start"], result["lesson_minutes"], result["break_minutes"],
            DEFAULT_PERIOD_COUNT,
        )
    return result


def validate_timing(value: dict) -> dict:
    """验证前端传入的完整作息，并返回可持久化的 JSON 数据。"""
    first_start = value["first_start"]
    _clock_minutes(first_start)
    lesson_minutes = int(value["lesson_minutes"])
    break_minutes = int(value["break_minutes"])
    periods = value["periods"]
    if not 15 <= lesson_minutes <= 180:
        raise ValueError("每节课时长应在 15–180 分钟之间")
    if not 0 <= break_minutes <= 180:
        raise ValueError("节间隔应在 0–180 分钟之间")
    if not MIN_PERIOD_COUNT <= len(periods) <= MAX_PERIOD_COUNT:
        raise ValueError(f"节数应在 {MIN_PERIOD_COUNT}–{MAX_PERIOD_COUNT} 之间")
    previous_end = -1
    for start, end in periods:
        start_minute = _clock_minutes(start)
        end_minute = _clock_minutes(end)
        if end_minute <= start_minute:
            raise ValueError("每节课的结束时间必须晚于开始时间")
        if start_minute < previous_end:
            raise ValueError("节次时间不能重叠，且必须按顺序排列")
        previous_end = end_minute
    term_start = value.get("term_start")
    if term_start is not None:
        parsed_term = date.fromisoformat(term_start)
        if parsed_term.weekday() != 0:
            raise ValueError("学期第一周的开始日期必须是周一")
    raw_segments = value.get("segments") if isinstance(value.get("segments"), dict) else {}
    segments = {
        key: raw_segments.get(key, default) for key, default in DEFAULT_SEGMENTS.items()
    }
    noon = _clock_minutes(segments["noon"])
    afternoon = _clock_minutes(segments["afternoon"])
    evening = _clock_minutes(segments["evening"])
    if not noon < afternoon < evening:
        raise ValueError("时段边界必须按 中午 < 下午 < 晚上 的顺序排列")
    return {
        "term_start": term_start,
        "first_start": first_start,
        "lesson_minutes": lesson_minutes,
        "break_minutes": break_minutes,
        "segments": segments,
        "periods": [[start, end] for start, end in periods],
    }


def timing_to_calendar(timing: dict) -> dict:
    """将课表自身的作息转换成约饭匹配使用的教学日历。"""
    normalized = normalize_timing(timing)
    if not normalized.get("term_start"):
        raise ValueError("请先在课表的作息设置中填写学期第一周周一")
    return {
        "term_start": normalized["term_start"],
        "periods": normalized["periods"],
    }
