"""Tests for the provider-agnostic structured vision adapter."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.engines.vision import SCOPE_PROMPT, VisionPreparationError, StructuredVisionAnalyzer, extract_video_keyframes
from app.models.domain import MediaAsset, SpaceType, WorkPhase


class FakeClient:
    def __init__(self):
        self.prompt = ""
        self.asset_paths: list[str] = []

    def complete_json(self, *, prompt: str, asset_paths: list[str]) -> dict:
        self.prompt = prompt
        self.asset_paths = asset_paths
        return {
            "spaces": [
                {
                    "space": "kitchen",
                    "area_m2": 14,
                    "condition": "poor",
                    "confidence": 0.92,
                    "requested_works": ["mep", "joinery"],
                    "notes": "کابینت فرسوده دیده می‌شود.",
                }
            ],
            "style": "modern",
            "assumptions": ["متراژ از تصویر قابل اندازه‌گیری دقیق نیست."],
        }


def test_structured_vision_adapter_validates_provider_json():
    client = FakeClient()
    analyzer = StructuredVisionAnalyzer(client)
    asset = MediaAsset(
        filename="kitchen.jpg",
        content_type="image/jpeg",
        size_bytes=10,
        stored_path="uploads/media/kitchen.jpg",
    )

    result = analyzer.observe([asset], "کابینت و لوله‌کشی آشپزخانه مشکل دارد")

    assert result.spaces[0].space is SpaceType.KITCHEN
    assert result.spaces[0].requested_works == [WorkPhase.MEP, WorkPhase.JOINERY]
    assert client.asset_paths == ["uploads/media/kitchen.jpg"]
    assert SCOPE_PROMPT in client.prompt
    assert "آشپزخانه" in client.prompt


def test_extracts_video_keyframes(monkeypatch, tmp_path):
    source = tmp_path / "walkthrough.mp4"
    source.write_bytes(b"video")
    asset = MediaAsset(
        filename="walkthrough.mp4", content_type="video/mp4", size_bytes=5,
        stored_path=str(source), is_video=True, frame_count=6,
    )

    def fake_run(command, **kwargs):
        frame_dir = Path(command[-1]).parent
        (frame_dir / "frame-01.jpg").write_bytes(b"frame")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("app.engines.vision.subprocess.run", fake_run)
    assert extract_video_keyframes(asset) == [str(tmp_path / "walkthrough-frames" / "frame-01.jpg")]


def test_video_frame_failure_is_explicit(monkeypatch, tmp_path):
    source = tmp_path / "walkthrough.mp4"
    source.write_bytes(b"video")
    asset = MediaAsset(
        filename="walkthrough.mp4", content_type="video/mp4", size_bytes=5,
        stored_path=str(source), is_video=True, frame_count=6,
    )
    monkeypatch.setattr("app.engines.vision.subprocess.run", lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()))
    with pytest.raises(VisionPreparationError):
        extract_video_keyframes(asset)
