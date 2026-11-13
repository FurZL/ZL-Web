"""个人空间布局端点契约测试（使用隔离的内存替身，不依赖真实服务）。"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.profile import router as profile_router
from app.core.config import settings
from app.core.database import get_db
from app.models.image import ProfileImage, StoredObject
from app.models.profile_layout import ProfileLayout
from app.services import profile_layout as profile_layout_service


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeDatabase:
    def __init__(self, user_id, images, stored_objects):
        self.user_id = user_id
        self.images = images
        self.stored_objects = stored_objects
        self.layouts = {}

    async def get(self, model, key):
        if model is ProfileLayout:
            return self.layouts.get(key)
        if model is ProfileImage:
            return next((image for image in self.images if image.id == key), None)
        return None

    async def execute(self, _statement):
        rows = []
        for image in self.images:
            stored = self.stored_objects.get(image.stored_object_id)
            if image.owner_id == self.user_id and image.is_displayable and stored is not None:
                rows.append((image, stored))
        return FakeResult(rows)

    async def scalar(self, _statement):
        return 12

    def add(self, value):
        if isinstance(value, ProfileLayout):
            self.layouts[value.user_id] = value

    async def commit(self):
        return None

    async def refresh(self, _value):
        return None


class FakeStorage:
    async def presign_download(self, bucket, object_key, expires_in=900):
        return f"signed://{bucket}/{object_key}?ttl={expires_in}"


@pytest.fixture
def profile_api(monkeypatch):
    user_id = "demo"
    user = type(
        "FakeUser",
        (),
        {
            "id": user_id,
            "created_at": datetime.now(UTC) - timedelta(days=268),
        },
    )()
    other_user_id = "other"
    image_specs = [
        (user_id, "private/profiles/demo/a1", True),
        (user_id, "private/profiles/demo/a2", True),
        (user_id, "private/profiles/demo/a3", False),
        (user_id, "private/profiles/other/aliased", True),
        (other_user_id, "private/profiles/other/a1", True),
    ]
    images = []
    stored_objects = {}
    for owner_id, object_key, is_displayable in image_specs:
        image_id = uuid.uuid4()
        stored_id = uuid.uuid4()
        images.append(
            ProfileImage(
                id=image_id,
                owner_id=owner_id,
                stored_object_id=stored_id,
                width=400,
                height=400,
                is_displayable=is_displayable,
                created_at=datetime.now(UTC),
            )
        )
        stored_objects[stored_id] = StoredObject(
            id=stored_id,
            bucket="private-bucket",
            object_key=object_key,
            processing_status="ready",
        )

    db = FakeDatabase(user_id, images, stored_objects)
    app = FastAPI()
    app.include_router(profile_router, prefix="/api/v1")

    async def fake_current_user():
        return user

    async def fake_db():
        yield db

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(profile_layout_service, "get_storage_provider", lambda: FakeStorage())
    return TestClient(app), db, images, user_id


@pytest.fixture
def seed_blocks():
    return [
        {
            "id": "seed-bio",
            "type": "bio",
            "span": 8,
            "props": {
                "text": (
                    "在杭州念书的毛茸茸爱好者，喜欢画图、拍照、听 Live。\n"
                    "周末一般在社团活动室出没。"
                )
            },
        },
        {
            "id": "seed-stats",
            "type": "stats",
            "span": 4,
            "props": {"items": ["joined_days", "gallery_image_count"]},
        },
        {
            "id": "seed-featured",
            "type": "featured_photo",
            "span": 12,
            "props": {
                "object_key": "private/profiles/demo/a1",
                "caption": "今年夏天的第一场漫展",
            },
        },
        {
            "id": "seed-wall",
            "type": "photo_wall",
            "span": 8,
            "props": {
                "object_keys": ["private/profiles/demo/a2", "private/profiles/demo/a1"],
                "columns": 2,
            },
        },
        {
            "id": "seed-links",
            "type": "links",
            "span": 4,
            "props": {
                "items": [
                    {"label": "社团公告", "url": "https://example.com/notices"},
                    {"label": "我的 Pixiv", "url": "https://example.com/pixiv"},
                ]
            },
        },
        {
            "id": "seed-quote",
            "type": "quote",
            "span": 6,
            "props": {"text": "毛好，人也好。", "author": "某位圈友"},
        },
        {
            "id": "seed-gallery",
            "type": "gallery_link",
            "span": 6,
            "props": {"tag": "漫展", "label": "看看现场照片"},
        },
    ]


def test_seed_layout_put_get_and_media_permissions(profile_api, seed_blocks):
    client, _db, _images, _user_id = profile_api
    response = client.put("/api/v1/profile/me/layout", json={"blocks": seed_blocks})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["draft_blocks"] == seed_blocks
    assert payload["published_blocks"] is None
    assert set(payload["media"]) == {
        "private/profiles/demo/a1",
        "private/profiles/demo/a2",
    }
    assert payload["media_expires_in"] == settings.private_url_ttl_seconds
    assert all(
        item["display_url"].endswith(f"ttl={settings.private_url_ttl_seconds}")
        for item in payload["media"].values()
    )

    get_response = client.get("/api/v1/profile/me/layout")
    assert get_response.status_code == 200
    assert get_response.json()["data"] == payload


def test_layout_validation_error_includes_block_id(profile_api, seed_blocks):
    client, _db, _images, _user_id = profile_api
    blocks = [dict(seed_blocks[0], span=99)]

    response = client.put("/api/v1/profile/me/layout", json={"blocks": blocks})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PROFILE_LAYOUT_INVALID"
    assert "seed-bio" in response.json()["detail"]["message"]


@pytest.mark.parametrize(
    "object_key",
    [
        "private/profiles/demo/a3",
        "private/profiles/other/a1",
        "private/profiles/other/aliased",
    ],
)
def test_layout_rejects_private_or_other_users_object_key(profile_api, object_key):
    client, _db, _images, _user_id = profile_api
    block = {
        "id": "seed-photo",
        "type": "featured_photo",
        "span": 12,
        "props": {
            "object_key": object_key,
            "caption": "other user's image",
        },
    }

    response = client.put("/api/v1/profile/me/layout", json={"blocks": [block]})

    assert response.status_code == 422
    assert object_key in response.json()["detail"]["message"]


def test_layout_drops_unknown_props_before_persisting(profile_api):
    client, db, _images, user_id = profile_api
    response = client.put(
        "/api/v1/profile/me/layout",
        json={
            "blocks": [
                {
                    "id": "seed-bio",
                    "type": "bio",
                    "span": 8,
                    "props": {"text": "hello", "unexpected": "discard me"},
                    "client_only": "discard me",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert db.layouts[user_id].draft_blocks == [
        {"id": "seed-bio", "type": "bio", "span": 8, "props": {"text": "hello"}}
    ]


def test_patch_image_displayable_and_non_owner_is_not_found(profile_api):
    client, _db, images, _user_id = profile_api
    own_image = images[0]
    response = client.patch(
        f"/api/v1/profile/me/images/{own_image.id}",
        json={"is_displayable": False},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": str(own_image.id),
        "is_displayable": False,
    }

    other_image = images[-1]
    response = client.patch(
        f"/api/v1/profile/me/images/{other_image.id}",
        json={"is_displayable": True},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROFILE_IMAGE_NOT_FOUND"
