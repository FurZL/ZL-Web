"""课表编辑契约：隔离数据验证权限、版本冲突、忙闲计算和隐私边界。"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.schedule import router
from app.core.database import get_db
from app.models.schedule import Schedule
from app.models.user import User


def entry(**changes):
    return {
        **dict(
            name="摄影约拍",
            location="秘密地点",
            campus="下沙校区",
            kind="event",
            weekday=0,
            lesson_start=3,
            lesson_end=4,
            weeks=[2],
        ),
        **changes,
    }


class ScheduleDatabase:
    def __init__(self, user):
        self.user = user
        self.rows = {}

    async def get(self, model, key):
        return self.rows.get(key) if model is Schedule else None

    async def scalar(self, statement):
        values = statement.compile().params
        return next(
            (
                s
                for s in self.rows.values()
                if s.id == values.get("id_1") and s.owner_id == values.get("owner_id_1")
            ),
            None,
        )

    async def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        values = statement.compile().params
        if entity is User:
            rows = [self.user] if values.get("username_1") == self.user.username else []
        else:
            rows = [s for s in self.rows.values() if s.owner_id == values.get("owner_id_1")]
            if "is_public IS true" in str(statement):
                rows = [s for s in rows if s.is_public]
            if "is_archived IS false" in str(statement):
                rows = [s for s in rows if not s.is_archived]
        return SimpleNamespace(all=lambda: rows, first=lambda: rows[0] if rows else None)

    def add(self, value):
        value.id = uuid.uuid4()
        value.created_at = datetime.now(UTC)
        self.rows[value.id] = value

    async def delete(self, value):
        del self.rows[value.id]

    async def commit(self):
        pass

    async def refresh(self, value):
        pass


@pytest.fixture
def api():
    owner = SimpleNamespace(id=uuid.uuid4(), username="owner", display_name="课表主人")
    viewer = SimpleNamespace(id=uuid.uuid4(), username="viewer", display_name="圈友")
    db = ScheduleDatabase(owner)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: owner
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client, app, db, owner, viewer


def test_create_edit_reload_delete_and_stale_save(api):
    client, _, db, _, _ = api
    created = client.post("/schedule/manual", json={"name": "秋季课表"})
    assert created.status_code == 201
    record = created.json()["data"]
    assert record["slots"] == [] and record["revision"] == 0
    assert record["is_public"] is False and record["format"] == "manual"
    path = f"/schedule/{record['id']}"
    saved = client.put(path + "/slots", json={"slots": [entry(weeks=[2, 1, 2])], "revision": 0})
    assert saved.status_code == 200
    assert saved.json()["data"]["slots"][0]["weeks"] == [1, 2]
    assert client.get(path).json()["data"]["revision"] == 1
    assert client.get("/schedule/mine").json()["data"]["items"][0]["slots"][0]["name"] == "摄影约拍"
    stale = client.put(path + "/slots", json={"slots": [], "revision": 0})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "SCHEDULE_CONFLICT"
    assert client.get(path).json()["data"]["slots"]
    assert client.put(path + "/slots", json={"slots": [], "revision": 1}).status_code == 200
    assert client.get(path).json()["data"]["slots"] == []
    assert client.delete(path).status_code == 200
    assert not db.rows


def test_timing_is_saved_with_schedule_and_uses_revision(api):
    client, _, _, _, _ = api
    record = client.post("/schedule/manual", json={"name": "有作息的课表"}).json()["data"]
    timing = {
        "term_start": "2026-09-07",
        "first_start": "08:10",
        "lesson_minutes": 45,
        "break_minutes": 10,
        "segments": {"noon": "11:30", "afternoon": "13:00", "evening": "17:30"},
        "periods": [
            [
                f"{8 + (10 + i * 55) // 60:02}:{(10 + i * 55) % 60:02}",
                f"{8 + (55 + i * 55) // 60:02}:{(55 + i * 55) % 60:02}",
            ]
            for i in range(14)
        ],
    }
    response = client.put(
        f"/schedule/{record['id']}/timing",
        json={"revision": 0, "timing": timing},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["timing"] == timing
    assert response.json()["data"]["revision"] == 1
    expanded = entry(lesson_start=13, lesson_end=14, weeks=[1])
    saved_slot = client.put(
        f"/schedule/{record['id']}/slots",
        json={"slots": [expanded], "revision": 1},
    )
    assert saved_slot.status_code == 200, saved_slot.text
    shrink = {**timing, "periods": timing["periods"][:12]}
    rejected_shrink = client.put(
        f"/schedule/{record['id']}/timing",
        json={"revision": 2, "timing": shrink},
    )
    assert rejected_shrink.status_code == 422
    assert rejected_shrink.json()["detail"]["code"] == "TIMING_TOO_SHORT"
    stale = client.put(
        f"/schedule/{record['id']}/timing",
        json={"revision": 0, "timing": timing},
    )
    assert stale.status_code == 409


def test_manual_schedule_accepts_imported_slots_and_explicit_timing(api):
    client, *_ = api
    periods = [
        [
            f"{(480 + i * 55) // 60:02}:{(480 + i * 55) % 60:02}",
            f"{(525 + i * 55) // 60:02}:{(525 + i * 55) % 60:02}",
        ]
        for i in range(14)
    ]
    timing = {
        "term_start": "2026-09-07",
        "first_start": "08:00",
        "lesson_minutes": 45,
        "break_minutes": 10,
        "segments": {"noon": "12:00", "afternoon": "14:00", "evening": "18:00"},
        "periods": periods,
    }
    response = client.post(
        "/schedule/manual",
        json={
            "name": "教务系统导入课表",
            "slots": [entry(lesson_start=13, lesson_end=14, weeks=[1, 3, 5])],
            "timing": timing,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["format"] == "manual"
    assert data["slots"][0]["lesson_start"] == 13
    assert data["slots"][0]["weeks"] == [1, 3, 5]
    assert data["timing"] == timing


def test_timing_segments_default_and_validation(api):
    from app.services.schedule_timing import default_timing, normalize_timing

    client, *_ = api
    legacy = default_timing(12)
    legacy.pop("segments", None)
    assert normalize_timing(legacy)["segments"] == {
        "noon": "12:00",
        "afternoon": "14:00",
        "evening": "18:00",
    }

    bad = {
        **default_timing(12),
        "segments": {"noon": "14:00", "afternoon": "12:00", "evening": "18:00"},
    }
    response = client.post("/schedule/manual", json={"name": "边界顺序错误", "timing": bad})
    assert response.status_code == 422


def test_manual_schedule_rejects_default_timing_that_crosses_midnight(api):
    client, *_ = api
    response = client.post(
        "/schedule/manual",
        json={
            "name": "晚间课表",
            "slots": [entry(lesson_start=18, lesson_end=18)],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "TIMING_REQUIRED"


def test_private_read_and_owner_only_writes(api):
    client, app, _, _, viewer = api
    record = client.post("/schedule/manual", json={"name": "私有课表", "slots": [entry()]}).json()[
        "data"
    ]
    path = f"/schedule/{record['id']}"
    app.dependency_overrides[get_current_user] = lambda: viewer
    assert client.get(path).status_code == 403
    assert client.get("/schedule/shared/owner").status_code == 404
    assert client.put(path + "/slots", json={"slots": [], "revision": 0}).status_code == 404
    assert client.patch(path + "/visibility", json={"is_public": True}).status_code == 404
    assert client.delete(path).status_code == 404


def test_all_shared_reads_redact_events_and_keep_course_details(api):
    client, app, db, owner, viewer = api
    record = client.post(
        "/schedule/manual",
        json={"name": "课表", "slots": [entry(), entry(kind="course", name="数学")]},
    ).json()["data"]
    path = f"/schedule/{record['id']}"
    assert (
        client.patch(path + "/visibility", json={"is_public": True}).json()["data"]["slots"][0][
            "name"
        ]
        == "摄影约拍"
    )
    app.dependency_overrides[get_current_user] = lambda: viewer
    for url in [path, "/schedule/shared/owner"]:
        slots = client.get(url).json()["data"]["slots"]
        assert slots[0]["name"] == "已有安排"
        assert slots[0]["location"] == "" and slots[0]["campus"] is None
        assert slots[0]["weeks"] == [2] and slots[0]["lesson_start"] == 3
        assert slots[1]["name"] == "数学" and slots[1]["location"] == "秘密地点"
    assert client.put(path + "/slots", json={"slots": [], "revision": 0}).status_code == 404
    app.dependency_overrides[get_current_user] = lambda: owner
    assert client.get(path).json()["data"]["slots"][0]["name"] == "摄影约拍"
    # 按 owner 查询的服务也必须脱敏；不改变持久化原文。
    import asyncio

    from app.services.schedule_service import get_public_schedule_by_owner

    public = asyncio.run(get_public_schedule_by_owner(db, owner.id))
    assert public["slots"][0]["name"] == "已有安排"
    client.patch(path + "/visibility", json={"is_public": False})
    app.dependency_overrides[get_current_user] = lambda: viewer
    assert client.get("/schedule/shared/owner").status_code == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "  "},
        {"lesson_start": 0},
        {"lesson_end": 25},
        {"lesson_start": 5, "lesson_end": 4},
        {"weekday": 7},
        {"weeks": []},
        {"weeks": [0]},
        {"weeks": [54]},
        {"weeks": [True]},
        {"weeks": [1.5]},
        {"kind": "admin"},
        {"unexpected": "data"},
    ],
)
def test_invalid_editor_input_rejected(api, changes):
    client, *_ = api
    response = client.post("/schedule/manual", json={"name": "测试", "slots": [entry(**changes)]})
    assert response.status_code == 422


def test_week_filter_and_personal_events_participate_in_compare(api):
    client, *_ = api
    body = {"slots_a": [entry()], "slots_b": [entry(kind="course", name="数学")], "week": 2}
    result = client.post("/schedule/compare", json=body).json()["data"]
    assert result["week"] == 2
    assert result["same_classroom"] == []  # 同地点的个人日程也不是同教室上课
    assert len(result["overlaps"]) == 1
    assert [s for s in result["both_free"] if s["weekday"] == 0] == [
        {"weekday": 0, "lesson_start": 1, "lesson_end": 2},
        {"weekday": 0, "lesson_start": 5, "lesson_end": 12},
    ]
    body["week"] = 3
    result = client.post("/schedule/compare", json=body).json()["data"]
    assert not result["overlaps"]
    assert result["both_free"][0] == {"weekday": 0, "lesson_start": 1, "lesson_end": 12}
    body["week"] = None
    assert len(client.post("/schedule/compare", json=body).json()["data"]["overlaps"]) == 1


def test_shelf_reorder_requires_full_owned_order(api):
    client, app, db, owner, viewer = api
    first = client.post("/schedule/manual", json={"name": "A"}).json()["data"]
    second = client.post("/schedule/manual", json={"name": "B"}).json()["data"]
    third = client.post("/schedule/manual", json={"name": "C"}).json()["data"]
    ids = [third["id"], first["id"], second["id"]]

    response = client.put("/schedule/order", json={"ids": ids})
    assert response.status_code == 200, response.text
    positions = {str(row.id): row.sort_order for row in db.rows.values()}
    assert positions[third["id"]] == 0
    assert positions[first["id"]] == 1
    assert positions[second["id"]] == 2

    missing = client.put("/schedule/order", json={"ids": ids[:2]})
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "ORDER_MISMATCH"
    duplicate = client.put("/schedule/order", json={"ids": [ids[0], ids[0], ids[1]]})
    assert duplicate.status_code == 409
    assert client.put("/schedule/order", json={"ids": []}).status_code == 409

    app.dependency_overrides[get_current_user] = lambda: viewer
    assert client.put("/schedule/order", json={"ids": ids}).status_code == 409


def test_legacy_records_default_course_and_revision(api):
    client, _, db, owner, _ = api
    slot = entry(kind="course")
    del slot["kind"]
    row = Schedule(owner_id=owner.id, parsed_json={"slots": [slot]}, is_public=False)
    db.add(row)
    data = client.get(f"/schedule/{row.id}").json()["data"]
    assert data["revision"] == 0 and data["slots"][0]["kind"] == "course"
    assert (
        client.put(
            f"/schedule/{row.id}/slots", json={"slots": data["slots"], "revision": 0}
        ).status_code
        == 200
    )


def test_shelf_rename_archive_restore_and_shared_visibility(api):
    client, app, db, owner, viewer = api
    record = client.post(
        "/schedule/manual", json={"name": "大一课表", "slots": [entry()]}
    ).json()["data"]
    path = f"/schedule/{record['id']}"

    renamed = client.patch(path, json={"original_name": " 2026 秋 · 大三课表 "})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["data"]["original_name"] == "2026 秋 · 大三课表"
    assert renamed.json()["data"]["is_archived"] is False
    assert client.patch(path, json={"original_name": "   "}).status_code == 422
    assert client.patch(path, json={}).status_code == 422

    assert client.patch(path + "/visibility", json={"is_public": True}).status_code == 200
    archived = client.patch(path, json={"is_archived": True})
    assert archived.status_code == 200, archived.text
    assert archived.json()["data"]["is_archived"] is True
    assert archived.json()["data"]["is_public"] is False
    assert client.get(path).status_code == 200
    assert client.get("/schedule/mine").json()["data"]["items"][0]["is_archived"] is True

    app.dependency_overrides[get_current_user] = lambda: viewer
    assert client.get("/schedule/shared/owner").status_code == 404
    # 直接改回 public，验证共享查询本身也会排除存档课表。
    db.rows[uuid.UUID(record["id"])].is_public = True
    assert client.get("/schedule/shared/owner").status_code == 404
    app.dependency_overrides[get_current_user] = lambda: owner

    blocked = client.patch(path + "/visibility", json={"is_public": True})
    assert blocked.status_code == 422
    assert blocked.json()["detail"]["code"] == "ARCHIVED_SCHEDULE"

    restored = client.patch(path, json={"is_archived": False})
    assert restored.status_code == 200
    assert restored.json()["data"]["is_archived"] is False
    assert client.patch(path + "/visibility", json={"is_public": True}).status_code == 200
    app.dependency_overrides[get_current_user] = lambda: viewer
    assert client.get("/schedule/shared/owner").json()["data"]["id"] == record["id"]
    assert client.patch(path, json={"original_name": "改别人的"}).status_code == 404
