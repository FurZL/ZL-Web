"""课表解析器测试（ICS / TXT / PDF 占位）。"""

import pytest

from app.services.schedule import (
    ScheduleParseError,
    parse_ics,
    parse_schedule,
    parse_txt,
)


def test_parse_ics():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:高等数学
LOCATION:2-N130
DTSTART:20260907T080000Z
DTEND:20260907T100000Z
RRULE:FREQ=WEEKLY;COUNT=16
END:VEVENT
END:VCALENDAR
""".encode("utf-8")
    slots = parse_ics(ics)
    assert len(slots) == 1
    assert slots[0].name == "高等数学"
    assert slots[0].location == "2-N130"
    assert slots[0].weekday == 0  # 周一
    assert slots[0].weeks == list(range(1, 17))


def test_parse_txt_zjut():
    txt = "周一\t高等数学★ (3-5节)1-11周/校区:下沙校区/场地:2-N130/教师:xxx\n".encode("utf-8")
    slots = parse_txt(txt)
    assert len(slots) == 1
    assert slots[0].name == "高等数学"
    assert slots[0].lesson_start == 3
    assert slots[0].lesson_end == 5
    assert slots[0].location == "2-N130"


def test_parse_schedule_pdf_placeholder():
    with pytest.raises(ScheduleParseError) as excinfo:
        parse_schedule(b"%PDF-fake", "schedule.pdf")
    assert excinfo.value.code == "PDF_UNSUPPORTED"


def test_parse_schedule_dispatches_by_extension():
    ics = "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:A\nDTSTART:20260907T080000Z\nDTEND:20260907T090000Z\nEND:VEVENT\nEND:VCALENDAR".encode("utf-8")
    result = parse_schedule(ics, "class.ics")
    assert result["format"] == "ics"
    assert len(result["slots"]) == 1