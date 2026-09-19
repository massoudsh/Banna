"""تست media pipeline (Issue #5)."""

import pytest

from app.engines.media import (
    MAX_FILE_BYTES,
    MediaValidationError,
    store_asset,
    validate_request,
    validate_upload,
)


class TestValidateUpload:
    def test_accepts_jpeg(self):
        validate_upload("room.jpg", "image/jpeg", 1024)

    def test_accepts_video(self):
        validate_upload("room.mp4", "video/mp4", 5_000_000)

    def test_rejects_unknown_type(self):
        with pytest.raises(MediaValidationError, match="پشتیبانی"):
            validate_upload("doc.pdf", "application/pdf", 1024)

    def test_rejects_empty_file(self):
        with pytest.raises(MediaValidationError, match="خالی"):
            validate_upload("room.jpg", "image/jpeg", 0)

    def test_rejects_oversized(self):
        with pytest.raises(MediaValidationError, match="حجم"):
            validate_upload("room.jpg", "image/jpeg", MAX_FILE_BYTES + 1)

    def test_accepts_exactly_at_limit(self):
        validate_upload("room.jpg", "image/jpeg", MAX_FILE_BYTES)

    def test_rejects_missing_extension(self):
        with pytest.raises(MediaValidationError, match="پسوند"):
            validate_upload("room", "image/jpeg", 1024)


class TestValidateRequest:
    def test_accepts_normal_request(self):
        validate_request(area_m2=80, media_count=3)

    def test_rejects_zero_area(self):
        with pytest.raises(MediaValidationError, match="متراژ"):
            validate_request(area_m2=0, media_count=3)

    def test_rejects_negative_area(self):
        with pytest.raises(MediaValidationError):
            validate_request(area_m2=-5, media_count=3)

    def test_rejects_huge_area_outside_mvp(self):
        with pytest.raises(MediaValidationError, match="۱۰۰۰"):
            validate_request(area_m2=5000, media_count=3)

    def test_requires_at_least_one_media(self):
        with pytest.raises(MediaValidationError, match="عکس"):
            validate_request(area_m2=80, media_count=0)


class TestStoreAsset:
    def test_stores_and_returns_asset(self, tmp_path):
        src = tmp_path / "photo.jpg"
        src.write_bytes(b"x" * 500)

        asset = store_asset(src, "abc123", tmp_path / "storage", content_type="image/jpeg")

        assert asset.size_bytes == 500
        assert asset.is_video is False
        assert asset.frame_count == 1
        assert (tmp_path / "storage" / "abc123.jpg").exists()

    def test_stored_name_ignores_user_filename(self, tmp_path):
        """رگرسیون امنیتی: نام فایل کاربر نباید در مسیر ذخیره اثر بگذارد."""
        src = tmp_path / "evil.jpg"
        src.write_bytes(b"x")

        asset = store_asset(src, "safe-id", tmp_path / "storage", content_type="image/jpeg")

        assert "evil" not in asset.stored_path
        assert asset.stored_path.endswith("safe-id.jpg")
        # نام اصلی برای نمایش حفظ می‌شود
        assert asset.filename == "evil.jpg"

    def test_marks_video_and_counts_frames(self, tmp_path):
        src = tmp_path / "clip.mp4"
        src.write_bytes(b"x" * 10)

        asset = store_asset(src, "vid1", tmp_path / "storage", content_type="video/mp4")

        assert asset.is_video is True
        assert asset.frame_count > 1

    def test_rejects_invalid_before_writing(self, tmp_path):
        src = tmp_path / "bad.txt"
        src.write_bytes(b"x")

        with pytest.raises(MediaValidationError):
            store_asset(src, "bad", tmp_path / "storage", content_type="text/plain")

        assert not (tmp_path / "storage" / "bad.txt").exists()

    def test_creates_storage_dir(self, tmp_path):
        src = tmp_path / "a.png"
        src.write_bytes(b"x")
        nested = tmp_path / "deep" / "nested"

        store_asset(src, "n1", nested, content_type="image/png")

        assert nested.exists()
