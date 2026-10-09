"""Adapter for structured multimodal Scope extraction (Issue #24).

The provider client is injected by deployment code so credentials and provider SDKs stay
outside the domain layer. The adapter accepts only schema-valid JSON responses.
"""

from __future__ import annotations

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


class StructuredVisionAnalyzer:
    """Converts a provider's JSON response into the project's ScopeSummary contract."""

    def __init__(self, client: MultimodalClient):
        self._client = client

    def observe(self, assets: list[MediaAsset], text: str) -> ScopeSummary:
        response = self._client.complete_json(
            prompt=f"{SCOPE_PROMPT}\n{text}",
            asset_paths=[asset.stored_path for asset in assets],
        )
        return ScopeSummary.model_validate(response)
