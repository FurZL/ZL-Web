"""权限矩阵测试。"""

from app.core.permissions import Role, has_permission, require_permission


def test_guest_cannot_upload():
    assert not has_permission(Role.GUEST, "gallery.image.upload")


def test_photographer_can_upload():
    assert has_permission(Role.PHOTOGRAPHER, "gallery.image.upload")


def test_member_cannot_publish():
    assert not has_permission(Role.MEMBER, "gallery.image.publish")


def test_admin_site_config():
    assert has_permission(Role.ADMIN, "site_config.manage")


def test_require_permission_raises():
    try:
        require_permission(Role.MEMBER, "user.approve")
        assert False, "应当抛出 PermissionError"
    except PermissionError:
        pass