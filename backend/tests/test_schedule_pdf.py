"""PDF 课表解析：跨页拼接、同格多课、API 预览契约。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints import schedule as schedule_endpoint
from app.services.schedule import CourseSlot
from app.services.schedule_pdf import (
    PdfParseError,
    PdfParseResult,
    _parse_cell_blocks,
    _parse_page,
    parse_pdf_schedule,
)


class FakePage:
    def __init__(self, table, text: str = ""):
        self.table = table
        self.text = text

    def extract_tables(self):
        return [self.table]

    def extract_text(self):
        return self.text


def _cell(name: str, periods: str, weeks: str, location: str, extra: str = "") -> str:
    return (
        f"{name}\n({periods}){weeks}/校区:下沙校\n区/场地:{location}/教师:测试\n{extra}"
    )


def test_cell_with_two_courses_and_wrapped_metadata():
    cell = (
        _cell("测试实验○", "1-7节", "12-16周", "3-N319-2", "教学班:(2026-2027-1)-1\n")
        + _cell("测试理论★", "3-5节", "1-11周", "2-N130", "学分:2.0")
    )
    pending: dict[int, list[str]] = {}
    warnings: list[str] = []

    slots = _parse_cell_blocks(cell, 1, pending, warnings)

    assert [slot.name for slot in slots] == ["测试实验", "测试理论"]
    assert [(slot.lesson_start, slot.lesson_end) for slot in slots] == [(1, 7), (3, 5)]
    assert [slot.weeks for slot in slots] == [list(range(12, 17)), list(range(1, 12))]
    assert slots[0].location == "3-N319-2"
    assert slots[0].campus == "下沙校区"
    assert slots[1].weekday == 1
    assert not warnings


def test_name_only_then_detail_on_next_page():
    pending: dict[int, list[str]] = {}
    warnings: list[str] = []

    assert _parse_cell_blocks("测试导论★", 0, pending, warnings) == []
    assert pending[0] == ["测试导论"]

    slots = _parse_cell_blocks(
        "(10-12节)1-11周/校区:下沙\n校区/场地:2-S215/教师:测试\n教师/教学班:(2026-2027-1)-1",
        0,
        pending,
        warnings,
    )

    assert len(slots) == 1
    assert slots[0].name == "测试导论"
    assert (slots[0].lesson_start, slots[0].lesson_end) == (10, 12)
    assert slots[0].weeks == list(range(1, 12))
    assert pending[0] == []
    assert not warnings


def test_page_maps_weekday_columns_and_skips_footer():
    table = [
        ["2026-2027学年第1学期", None, None, None, None, None, None, None, None],
        ["时间段", "节次", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
        ["上午", "1", _cell("测试课★", "1-2节", "1-8周", "2-N101"), "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        ["实践课程：测试●教师/1-4周/无;", "", "", "", "", "", "", "", ""],
    ]
    page = FakePage(table, "2026-2027学年第1学期")

    slots, columns = _parse_page(page, None, {}, [])

    assert columns == {2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6}
    assert len(slots) == 1
    assert slots[0].weekday == 0
    assert slots[0].name == "测试课"


def test_missing_weeks_is_reported():
    pending: dict[int, list[str]] = {}
    warnings: list[str] = []

    slots = _parse_cell_blocks("测试课★\n(1-2节)/校区:下沙校区", 2, pending, warnings)

    assert slots == []
    assert any("周次" in warning for warning in warnings)


def test_invalid_pdf_rejected():
    with pytest.raises(PdfParseError) as error:
        parse_pdf_schedule(b"not a pdf")

    assert error.value.code == "PDF_INVALID"


@pytest.fixture
def pdf_api(monkeypatch):
    app = FastAPI()
    app.include_router(schedule_endpoint.router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="u", username="u")
    with TestClient(app) as client:
        yield client


def test_pdf_preview_response_shape(pdf_api, monkeypatch):
    monkeypatch.setattr(
        schedule_endpoint,
        "parse_pdf_schedule",
        lambda data: PdfParseResult(
            slots=[
                CourseSlot(
                    name="测试课",
                    location="2-N101",
                    weekday=0,
                    lesson_start=1,
                    lesson_end=2,
                    weeks=[1, 2, 3],
                    campus="下沙校区",
                )
            ],
            warnings=["有 1 门课程只有名称、没有时间安排，已忽略"],
            suggested_name="2026-2027-1 课表",
        ),
    )

    response = pdf_api.post(
        "/schedule/pdf-preview",
        files={"file": ("课表.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["suggested_name"] == "2026-2027-1 课表"
    assert data["slots"][0]["name"] == "测试课"
    assert data["slots"][0]["weeks"] == [1, 2, 3]
    assert data["warnings"]


def test_pdf_preview_maps_parse_errors(pdf_api, monkeypatch):
    def raise_error(data):
        raise PdfParseError("PDF_NO_TEXT", "未检测到文字层，可能是扫描件")

    monkeypatch.setattr(schedule_endpoint, "parse_pdf_schedule", raise_error)

    response = pdf_api.post(
        "/schedule/pdf-preview",
        files={"file": ("scan.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PDF_NO_TEXT"
