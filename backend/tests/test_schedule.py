"""课表解析与对比测试。"""

from app.services.schedule import CourseSlot, compare, parse_weeks, parse_zjut_cell


def test_parse_weeks_continuous():
    assert parse_weeks("1-16周") == list(range(1, 17))


def test_parse_weeks_single():
    assert parse_weeks("1,3,5周") == [1, 3, 5]


def test_parse_zjut_cell():
    cell = "高等数学★ (3-5节)1-11周/校区:下沙校区/场地:2-N130/教师:xxx"
    slots = parse_zjut_cell(cell, weekday=0)
    assert len(slots) == 1
    assert slots[0].name == "高等数学"
    assert slots[0].lesson_start == 3
    assert slots[0].lesson_end == 5
    assert slots[0].weeks == list(range(1, 12))
    assert slots[0].campus == "下沙校区"
    assert slots[0].location == "2-N130"


def test_compare_overlap_weeks():
    a = [
        CourseSlot(
            name="A课", location="1-N101", weekday=0,
            lesson_start=1, lesson_end=2, weeks=[1, 2, 3],
        )
    ]
    b = [
        CourseSlot(
            name="B课", location="1-N202", weekday=0,
            lesson_start=3, lesson_end=4, weeks=[1, 2, 3],
        )
    ]
    result = compare(a, b)
    # 节次不重叠 => 无冲突
    assert result["overlaps"] == []
    assert result["same_classroom"] == []


def test_compare_same_classroom():
    a = [
        CourseSlot(
            name="A课", location="1-N101", weekday=0,
            lesson_start=1, lesson_end=2, weeks=[1, 2, 3],
        )
    ]
    b = [
        CourseSlot(
            name="B课", location="1-N101", weekday=0,
            lesson_start=2, lesson_end=2, weeks=[1, 2, 3],
        )
    ]
    result = compare(a, b)
    assert len(result["same_classroom"]) == 1


def test_compare_weeks_no_overlap():
    a = [
        CourseSlot(
            name="A课", location="1-N101", weekday=0,
            lesson_start=1, lesson_end=2, weeks=[1, 2, 3],
        )
    ]
    b = [
        CourseSlot(
            name="B课", location="1-N101", weekday=0,
            lesson_start=1, lesson_end=2, weeks=[4, 5, 6],
        )
    ]
    result = compare(a, b)
    # 同名同位置同时间但周次不重叠 => 不算冲突
    assert result["same_classroom"] == []
    assert result["overlaps"] == []