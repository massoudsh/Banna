"""Adapter for structured multimodal Scope extraction (Issue #24).

The provider client is injected by deployment code so credentials and provider SDKs stay
outside the domain layer. The adapter accepts only schema-valid JSON responses.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Protocol

from app.models.domain import MediaAsset, ScopeSummary


class MultimodalClient(Protocol):
    """Minimal provider boundary; implementation owns authentication and transport."""

    def complete_json(self, *, prompt: str, asset_paths: list[str]) -> dict: ...


SCOPE_PROMPT = """تو تحلیلگر فنی بازسازی مسکونی در ایران هستی.
فقط JSON سازگار با ScopeSummary برگردان و حدس غیرقابل مشاهده نزن.
برای هر فضا space، area_m2، condition، confidence، requested_works و notes بده.
condition فقط good/fair/poor و space فقط kitchen/bathroom/living_room/bedroom باشد.
confidence بین ۰ و ۱ است. requested_works فقط demolition/mep/structure/covering/joinery/finish.
هر محدودیت مشاهده یا ابهام را در assumptions ثبت کن. توضیح کارفرما:
"""


class VisionPreparationError(RuntimeError):
    """ویدیو پیش از ارسال به provider به فریم قابل‌تحلیل تبدیل نشد."""


def extract_video_keyframes(asset: MediaAsset, *, max_frames: int = 6) -> list[str]:
    """فریم‌های پراکندهٔ ویدیو را با ffmpeg برای تحلیل چندوجهی استخراج می‌کند."""
    if not asset.is_video:
        return [asset.stored_path]
    source = Path(asset.stored_path)
    frame_dir = source.parent / f"{source.stem}-frames"
    frame_dir.mkdir(exist_ok=True)
    pattern = frame_dir / "frame-%02d.jpg"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(source), "-vf", "fps=1/5,scale=min(1280\\,iw):-2",
                "-frames:v", str(max_frames), str(pattern),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise VisionPreparationError("استخراج فریم کلیدی ویدیو ناموفق بود.") from exc
    frames = sorted(str(frame) for frame in frame_dir.glob("frame-*.jpg"))
    if not frames:
        raise VisionPreparationError("هیچ فریم قابل‌تحلیلی از ویدیو استخراج نشد.")
    return frames


class StructuredVisionAnalyzer:
    """Converts a provider's JSON response into the project's ScopeSummary contract."""

    def __init__(self, client: MultimodalClient):
        self._client = client

    def observe(self, assets: list[MediaAsset], text: str) -> ScopeSummary:
        response = self._client.complete_json(
            prompt=f"{SCOPE_PROMPT}\n{text}",
            asset_paths=[path for asset in assets for path in extract_video_keyframes(asset)],
        )
        return ScopeSummary.model_validate(response)
