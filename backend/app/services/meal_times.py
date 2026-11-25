"""将参与者确认的教学周和作息投影到北京时间，取忙时并集的补集。"""

from datetime import date, datetime, time, timedelta, timezone

CAMPUS = timezone(timedelta(hours=8))
MINUTE = timedelta(minutes=1)
DAY = timedelta(days=1)


def clock(day, hhmm):
    return datetime.combine(day, time.fromisoformat(hhmm), CAMPUS)


def busy_intervals(window, calendars, events):
    """Include all course/event slots from each selected schedule, and account-wide dated events."""
    intervals = [
        (e.starts_at - MINUTE * e.buffer_minutes, e.ends_at + MINUTE * e.buffer_minutes)
        for e in events
    ]
    for slots, calendar in calendars:
        anchor = date.fromisoformat(calendar["term_start"])
        periods = calendar["periods"]
        day = window.date_from - DAY  # buffers can cross midnight
        while day <= window.date_to + DAY:
            week = (day - anchor).days // 7 + 1
            for s in slots:
                if s["weekday"] == day.weekday() and (not s["weeks"] or week in s["weeks"]):
                    intervals.append(
                        (
                            clock(day, periods[s["lesson_start"] - 1][0]),
                            clock(day, periods[s["lesson_end"] - 1][1]),
                        )
                    )
            day += DAY
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def available(start, end, busy, buffer, now):
    return start - buffer >= now and not any(
        a < end + buffer and start - buffer < b for a, b in busy
    )


def recommend(window, busy, now):
    # Offer different dates before adding variations on the same date.
    by_day = []
    day = max(window.date_from, now.astimezone(CAMPUS).date())
    length, buffer = MINUTE * window.duration_minutes, MINUTE * window.buffer_minutes
    while day <= window.date_to:
        first, last = clock(day, window.daily_start), clock(day, window.daily_end)
        starts = set()
        cursor = first
        while cursor + length <= last:
            starts.add(cursor)
            cursor += 15 * MINUTE
        # Keep exact boundary times, including gaps shorter than the 15-minute grid.
        for _, end in busy:
            boundary = end + buffer
            if boundary.second or boundary.microsecond:
                boundary = (boundary + MINUTE).replace(second=0, microsecond=0)
            if first <= boundary <= last - length:
                starts.add(boundary)
        starts.add(last - length)
        starts = [s for s in starts if available(s, s + length, busy, buffer, now)]
        starts.sort(key=lambda s: (abs(s - (first + (last - first - length) / 2)), s))
        if starts:
            by_day.append(starts)
        day += DAY
    result = []
    for rank in range(max((len(d) for d in by_day), default=0)):
        for day_slots in by_day:
            if rank < len(day_slots):
                s = day_slots[rank].astimezone(CAMPUS)
                result.append(
                    {
                        "id": s.strftime("%Y%m%dT%H%M"),
                        "starts_at": s.isoformat(),
                        "ends_at": (s + length).isoformat(),
                    }
                )
                if len(result) == 5:
                    return result
    return result
