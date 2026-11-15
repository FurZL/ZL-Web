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
from app.models.user import User
from app.services import profile_layout as profile_layout_service


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeDatabase:
    def __init__(self, user_id, images, stored_objects, public_user):
        self.user_id = user_id
        self.images = images
        self.stored_objects = stored_objects
        self.public_user = public_user
        self.layouts = {}

    async def get(self, model, key):
        if model is ProfileLayout:
            return self.layouts.get(key)
        if model is ProfileImage:
            return next((image for image in self.images if image.id == key), None)
        return None

    async def execute(self, statement):
        entities = [description.get("entity") for description in statement.column_descriptions]
        if entities == [User]:
            user = self.public_user
            if (
                user is None
                or user.status != "active"
                or not user.is_active
            ):
                return FakeResult([])
            return FakeResult([user])

        rows = []
        for image in self.images:
            stored = self.stored_objects.get(image.stored_object_id)
            if image.owner_id == self.user_id and stored is not None:
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
            "username": "demo",
            "display_name": "示例成员",
            "avatar_url": None,
            "email": "private@example.com",
            "phone_e164": "+8613800000000",
            "status": "active",
            "is_active": True,
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
            visibility="private",
            processing_status="ready",
        )

    db = FakeDatabase(user_id, images, stored_objects, user)
    app = FastAPI()
    app.include_router(profile_router, prefix="/api/v1")

    async def fake_current_user():
        return user

    async def fake_db():
        yield db

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(profile_layout_service, "get_storage_provider", lambda: FakeStorage())
    monkeypatch.setattr(
        profile_layout_service,
        "get_avatar_public_url",
        lambda _user: "https://assets.example.test/avatar.webp",
    )
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


def test_publish_rejects_empty_draft(profile_api):
    client, _db, _images, _user_id = profile_api
    client.put("/api/v1/profile/me/layout", json={"blocks": []})

    response = client.post("/api/v1/profile/me/layout/publish")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PROFILE_LAYOUT_EMPTY"


def test_publish_and_discard_restore_published_blocks(profile_api):
    client, _db, _images, _user_id = profile_api
    published_block = {
        "id": "published-bio",
        "type": "bio",
        "span": 12,
        "props": {"text": "published"},
    }
    draft_block = {
        "id": "draft-bio",
        "type": "bio",
        "span": 12,
        "props": {"text": "draft"},
    }
    client.put("/api/v1/profile/me/layout", json={"blocks": [published_block]})

    publish_response = client.post("/api/v1/profile/me/layout/publish")

    assert publish_response.status_code == 200
    assert publish_response.json()["data"]["published_at"].endswith("+00:00")
    client.put("/api/v1/profile/me/layout", json={"blocks": [draft_block]})

    discard_response = client.post("/api/v1/profile/me/layout/discard")

    assert discard_response.status_code == 200
    assert discard_response.json()["data"]["draft_blocks"] == [published_block]
    assert discard_response.json()["data"]["published_blocks"] == [published_block]


def test_theme_update_validates_assets_and_returns_layout_payload(profile_api):
    client, _db, _images, _user_id = profile_api
    theme = {
        "primary": "#123ABC",
        "accent": "#FEDCBA",
        "background_type": "image",
        "background_key": "private/profiles/demo/a1",
        "background_blur": 12,
        "card_style": "outline",
    }

    response = client.put("/api/v1/profile/me/theme", json=theme)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["theme"] == theme
    assert payload["draft_blocks"] == []
    assert payload["media"][theme["background_key"]]["display_url"].endswith(
        f"ttl={settings.private_url_ttl_seconds}"
    )


@pytest.mark.parametrize(
    "override",
    [
        {"primary": "purple"},
        {"background_type": "video"},
        {"background_key": ""},
        {"background_blur": 21},
        {"card_style": "transparent"},
        {"unexpected": True},
    ],
)
def test_theme_update_rejects_invalid_fields(profile_api, override):
    client, _db, _images, _user_id = profile_api
    theme = {
        "primary": "#6B5CE7",
        "accent": "#F0A6C8",
        "background_type": "gradient",
        "background_key": None,
        "background_blur": 0,
        "card_style": "glass",
        **override,
    }

    response = client.put("/api/v1/profile/me/theme", json=theme)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PROFILE_THEME_INVALID"


def test_theme_update_rejects_private_or_other_user_background(profile_api):
    client, _db, _images, _user_id = profile_api
    theme = {
        "primary": "#6B5CE7",
        "accent": "#F0A6C8",
        "background_type": "image",
        "background_key": "private/profiles/other/a1",
        "background_blur": 0,
        "card_style": "glass",
    }

    response = client.put("/api/v1/profile/me/theme", json=theme)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PROFILE_THEME_INVALID"


def test_my_media_lists_all_own_images_with_visibility_state(profile_api):
    client, _db, _images, _user_id = profile_api

    response = client.get("/api/v1/profile/me/media")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 3
    assert {item["object_key"] for item in items} == {
        "private/profiles/demo/a1",
        "private/profiles/demo/a2",
        "private/profiles/demo/a3",
    }
    hidden = next(item for item in items if item["object_key"].endswith("/a3"))
    assert hidden["is_displayable"] is False
    assert hidden["display_url"].startswith("signed://private-bucket/")
    assert all("id" in item and "created_at" in item for item in items)


def test_public_page_is_anonymous_and_uses_only_published_displayable_media(
    profile_api, seed_blocks
):
    client, _db, images, _user_id = profile_api
    client.put("/api/v1/profile/me/layout", json={"blocks": seed_blocks})
    assert client.post("/api/v1/profile/me/layout/publish").status_code == 200
    draft_only = {
        "id": "draft-only",
        "type": "bio",
        "span": 12,
        "props": {"text": "not public"},
    }
    client.put("/api/v1/profile/me/layout", json={"blocks": [draft_only]})
    images[0].is_displayable = False
    client.app.dependency_overrides.pop(get_current_user)

    response = client.get("/api/v1/profile/demo/page")

    assert response.status_code == 200
    page = response.json()["data"]
    assert page["blocks"] == seed_blocks
    assert "draft-only" not in str(page["blocks"])
    assert set(page["media"]) == {"private/profiles/demo/a2"}
    assert set(page["user"]) == {"username", "display_name", "avatar_url"}
    assert page["user"]["avatar_url"] == "https://assets.example.test/avatar.webp"
    assert "email" not in page["user"] and "phone_e164" not in page["user"]
    assert "id" not in page["user"]


@pytest.mark.parametrize(
    "scenario",
    ["missing_user", "inactive_status", "inactive_flag", "no_layout", "unpublished", "private"],
)
def test_public_page_uses_same_not_found_for_ineligible_profiles(profile_api, scenario):
    client, db, _images, _user_id = profile_api
    block = {
        "id": "bio-1",
        "type": "bio",
        "span": 12,
        "props": {"text": "private"},
    }
    if scenario == "missing_user":
        db.public_user = None
    elif scenario == "inactive_status":
        db.public_user.status = "disabled"
    elif scenario == "inactive_flag":
        db.public_user.is_active = False
    elif scenario == "unpublished":
        client.put("/api/v1/profile/me/layout", json={"blocks": [block]})
    elif scenario == "private":
        client.put(
            "/api/v1/profile/me/layout",
            json={"blocks": [block], "is_public": False},
        )
        client.post("/api/v1/profile/me/layout/publish")
    client.app.dependency_overrides.pop(get_current_user)

    response = client.get("/api/v1/profile/demo/page")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "PROFILE_PAGE_NOT_FOUND",
        "message": "该用户还没有公开主页",
    }
