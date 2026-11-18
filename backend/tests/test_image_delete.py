"""公开图库删除：权限与对象存储清理测试。"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.images import router as images_router
from app.core.database import get_db
from app.models.image import Image, StoredObject
from app.providers import factory as provider_factory


class FakeUser:
    def __init__(self, role: str = "member") -> None:
        self.id = uuid.uuid4()
        self.role = role


class FakeResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value

    def all(self):
        return self._value


class FakeDatabase:
    def __init__(self, image: Image, stored: StoredObject) -> None:
        self.image = image
        self.stored = stored
        self.deleted = []

    async def get(self, model, key):
        if model is Image and key == self.image.id:
            return self.image
        if model is StoredObject and key == self.stored.id:
            return self.stored
        return None

    async def delete(self, value):
        self.deleted.append(value)

    async def commit(self):
        return None


class FakeStorage:
    def __init__(self) -> None:
        self.deleted = []

    async def delete_object(self, bucket, object_key):
        self.deleted.append((bucket, object_key))


def _client(monkeypatch, *, uploader_id, role: str):
    stored = StoredObject(
        id=uuid.uuid4(),
        bucket="gallery-bucket",
        object_key="public/gallery/original/2026/11/token",
        visibility="public",
        processing_status="ready",
    )
    image = Image(
        id=uuid.uuid4(),
        stored_object_id=stored.id,
        uploader_id=uploader_id,
        moderation_status="approved",
        is_public=True,
    )
    db = FakeDatabase(image, stored)
    storage = FakeStorage()
    user = FakeUser(role)
    app = FastAPI()
    app.include_router(images_router, prefix="/api/v1")

    async def fake_user():
        return user

    async def fake_db():
        yield db

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(provider_factory, "get_storage_provider", lambda: storage)
    return TestClient(app), db, storage, image, stored


def test_owner_can_delete_public_image_and_storage_objects(monkeypatch):
    owner = FakeUser("member")
    client, db, storage, image, stored = _client(monkeypatch, uploader_id=owner.id, role=owner.role)
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: owner

    response = client.delete(f"/api/v1/images/{image.id}")

    assert response.status_code == 200
    assert image in db.deleted
    assert stored in db.deleted
    assert (stored.bucket, stored.object_key) in storage.deleted
    assert len(storage.deleted) == 3


def test_other_member_cannot_delete_someone_elses_public_image(monkeypatch):
    owner = FakeUser("member")
    other = FakeUser("member")
    client, db, storage, image, stored = _client(monkeypatch, uploader_id=owner.id, role=other.role)
    app = client.app
    app.dependency_overrides[get_current_user] = lambda: other

    response = client.delete(f"/api/v1/images/{image.id}")

    assert response.status_code == 403
    assert db.deleted == []
    assert storage.deleted == []
