"""图片处理服务单元测试。"""

import io

import pytest
from PIL import Image as PILImage

from app.services import image_processing as proc


def test_derive_keys():
    original = "public/gallery/original/2026/11/abc123"
    from app.core.config import settings
    assert proc.derive_display_key(original) == (
        f"public/gallery/derived/2026/11/abc123/display_{settings.image_display_max_px}.webp"
    )
    assert proc.derive_thumb_key(original) == (
        f"public/gallery/derived/2026/11/abc123/thumb_{settings.image_thumb_max_px}.webp"
    )


def test_derive_key_rejects_non_gallery():
    with pytest.raises(ValueError):
        proc.derive_display_key("private/profiles/u1/abc")


def _make_png(w: int, h: int) -> bytes:
    img = PILImage.new("RGB", (w, h), (120, 80, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_resize_and_encode_webp():
    img = proc._decode(_make_png(3000, 2000))
    resized = proc._resize(img, 400)
    assert max(resized.size) <= 400

    webp = proc._encode_webp(resized, 85)
    assert webp[:4] == b"RIFF"
    # 能重新解码
    back = PILImage.open(io.BytesIO(webp))
    assert back.format == "WEBP"


def test_small_image_not_upscaled():
    img = proc._decode(_make_png(100, 100))
    resized = proc._resize(img, 400)
    assert resized.size == (100, 100)