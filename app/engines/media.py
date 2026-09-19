"""Media pipeline — دریافت، اعتبارسنجی و پیش‌پردازش ورودی چندرسانه‌ای (Issue #5)."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.models.domain import MediaAsset

MAX_FILE_BYTES = 25 * 1024 * 1024  # 25MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


class MediaValidationError(ValueError):
    """ورودی رد شد — پیام برای نمایش مستقیم به کاربر."""


def validate_upload(filename: str, content_type: str, size_bytes: int) -> None:
    """اعتبارسنجی پیش از ذخیره. ترتیب بررسی‌ها عمدی است."""
    if content_type not in ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES:
        raise MediaValidationError(
            f"فرمت فایل پشتیبانی نمی‌شود: {content_type}. "
            "فقط عکس (JPG/PNG/WEBP) یا ویدیو (MP4/MOV/WEBM) مجاز است."
        )
    if size_bytes <= 0:
        raise MediaValidationError("فایل خالی است.")
    if size_bytes > MAX_FILE_BYTES:
        raise MediaValidationError(
            f"حجم فایل {size_bytes // (1024 * 1024)}MB است؛ حداکثر مجاز "
            f"{MAX_FILE_BYTES // (1024 * 1024)}MB."
        )
    if not Path(filename).suffix:
        raise MediaValidationError("نام فایل پسوند معتبر ندارد.")


def store_asset(
    source: Path,
    asset_id: str,
    storage_dir: Path,
    *,
    content_type: str,
    estimate_video_frames: int = 6,
) -> MediaAsset:
    """ذخیرهٔ امن فایل و تولید MediaAsset.

    نام فایل ذخیره‌شده از `asset_id` ساخته می‌شود نه از نام کاربر، تا از
    path traversal و برخورد نام‌ها جلوگیری شود.
    """
    size_bytes = source.stat().st_size
    validate_upload(source.name, content_type, size_bytes)

    is_video = content_type in ALLOWED_VIDEO_TYPES
    suffix = Path(source.name).suffix.lower()
    storage_dir.mkdir(parents=True, exist_ok=True)
    target = storage_dir / f"{asset_id}{suffix}"

    shutil.copyfile(source, target)

    return MediaAsset(
        filename=source.name,
        content_type=content_type,
        size_bytes=size_bytes,
        stored_path=str(target),
        is_video=is_video,
        # در MVP فریم کلیدی واقعی استخراج نمی‌شود؛ فقط تعداد تقریبی برای مرحلهٔ
        # تحلیل بصری اعلام می‌شود (وابسته به ffmpeg در محیط اجرا).
        frame_count=estimate_video_frames if is_video else 1,
    )


def validate_request(
    *, area_m2: float | None, media_count: int, description: str = ""
) -> None:
    """اعتبارسنجی ورودی فرم پروژه (Issue #5).

    رسانه و متراژ هر دو اختیاری‌اند، ولی **حداقل یکی از سه ورودی** (رسانه،
    متراژ، توضیح متنی) باید وجود داشته باشد؛ در غیر این صورت چیزی برای پردازش
    نیست و خطا باید به کاربر گفته شود نه اینکه تخمین بی‌مبنا تولید شود.
    """
    if area_m2 is not None and area_m2 <= 0:
        raise MediaValidationError("متراژ باید بزرگ‌تر از صفر باشد.")
    if area_m2 is not None and area_m2 > 1000:
        raise MediaValidationError("متراژ بیش از ۱۰۰۰ مترمربع خارج از دامنهٔ MVP است.")
    if media_count == 0 and area_m2 is None and not description.strip():
        raise MediaValidationError(
            "برای شروع، حداقل متراژ یا توضیح پروژه لازم است (عکس/ویدیو اختیاری است)."
        )
