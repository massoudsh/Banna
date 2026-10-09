"""Tests for the provider-agnostic structured vision adapter."""

from app.engines.vision import SCOPE_PROMPT, StructuredVisionAnalyzer
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
