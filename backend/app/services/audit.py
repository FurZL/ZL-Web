"""Transactional, allowlisted audit records for administrative mutations."""

from datetime import date, datetime
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.content import Announcement, DynamicPage
from app.models.event import Event, EventRegistration
from app.models.image import Image
from app.models.image_job import ImageProcessingJob
from app.models.report import Report
from app.models.setting import SiteSetting
from app.models.user import User
from app.utils import mask_ip

# Only deliberately chosen fields may enter audit metadata. Large or sensitive
# payloads are represented by their field name, not their contents.
FIELDS = {
    User: ("user", {"role", "status", "is_active"}, set()),
    SiteSetting: ("site_setting", {"category", "is_public"}, {"value_json"}),
    Image: ("image", {"moderation_status", "is_public"}, {"tags"}),
    Report: ("report", {"status", "handled_at"}, set()),
    ImageProcessingJob: ("image_job", {"status", "attempts"}, set()),
    Announcement: ("announcement", {"status", "is_pinned", "published_at", "expires_at"}, {"title", "content"}),
    Event: ("event", {"status", "starts_at", "ends_at", "capacity", "registration_starts_at", "registration_ends_at"}, {"title", "description", "location"}),
    EventRegistration: ("event_registration", {"status", "checkin_at"}, set()),
    DynamicPage: ("page", {"status", "starts_at", "ends_at", "published_at"}, {"slug", "title", "schema_json", "seo_title", "seo_description"}),
}
SAFE_SETTING_FLAGS = {
    "registration_config": {"registration_enabled", "require_email_verification", "require_phone_verification"},
    "oauth_config": {"enabled", "qq_enabled"},
}


def _value(value):
    if isinstance(value, (datetime, date, UUID)):
        return str(value)
    return value


def _collect(session, _flush_context, _instances):
    context = session.info.get("admin_audit")
    if not context:
        return
    pending = session.info.setdefault("audit_pending", [])
    for operation, objects in (("create", session.new), ("update", session.dirty), ("delete", session.deleted)):
        for obj in list(objects):
            spec = FIELDS.get(type(obj))
            if spec is None or (operation == "update" and obj in session.deleted):
                continue
            target, safe_fields, hidden_fields = spec
            state = inspect(obj)
            before, after, changed = {}, {}, []
            for name in sorted(safe_fields | hidden_fields):
                history = state.attrs[name].history
                if operation == "update" and not history.has_changes():
                    continue
                changed.append(name)
                if name in safe_fields:
                    if operation == "update":
                        before[name] = _value(history.deleted[0]) if history.deleted else None
                        after[name] = _value(history.added[0]) if history.added else None
                    elif operation == "delete":
                        before[name] = _value(getattr(obj, name))
                    else:
                        after[name] = _value(getattr(obj, name))
            if isinstance(obj, SiteSetting) and "value_json" in changed:
                history = state.attrs.value_json.history
                old = history.deleted[0] if history.deleted and isinstance(history.deleted[0], dict) else {}
                new = history.added[0] if history.added and isinstance(history.added[0], dict) else {}
                for flag in SAFE_SETTING_FLAGS.get(obj.key, set()):
                    if old.get(flag) != new.get(flag) and all(v is None or isinstance(v, bool) for v in (old.get(flag), new.get(flag))):
                        before[flag], after[flag] = old.get(flag), new.get(flag)
            if operation == "update" and not changed:
                continue
            pending.append((obj, target, operation, {"before": before, "after": after, "fields_changed": changed}))


def _write(session, _flush_context):
    context = session.info.get("admin_audit")
    for obj, target, operation, changes in session.info.pop("audit_pending", []):
        target_id = obj.key if isinstance(obj, SiteSetting) else obj.id
        session.add(AuditLog(
            actor_user_id=context["actor_id"], action=f"{target}.{context['operation']}",
            target_type=target, target_id=str(target_id), request_id=context["request_id"],
            ip_masked=context["ip_masked"], metadata_json={"operation": operation, **changes},
        ))


async def audit_admin_mutation(
    request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        yield
        return
    session = db.sync_session
    session.info["admin_audit"] = {
        "actor_id": user.id,
        "operation": request.scope["endpoint"].__name__,
        "request_id": str(getattr(request.state, "request_id", ""))[:64] or None,
        "ip_masked": mask_ip(request.client.host) if request.client else None,
    }
    event.listen(session, "before_flush", _collect)
    event.listen(session, "after_flush_postexec", _write)
    try:
        yield
    finally:
        event.remove(session, "before_flush", _collect)
        event.remove(session, "after_flush_postexec", _write)
        session.info.pop("admin_audit", None)
        session.info.pop("audit_pending", None)
