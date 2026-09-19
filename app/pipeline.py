"""Orchestrator — اجرای زنجیرهٔ کامل از ورودی خام تا Brief نهایی.

هر مرحله خروجی ساختاریافته می‌دهد، بنابراین می‌توان در هر نقطه متوقف شد و
از همان‌جا ادامه داد (لازمهٔ ویرایش خروجی توسط کاربر — Issue #7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.engines import brief as brief_engine
from app.engines import material as material_engine
from app.engines import scenario as scenario_engine
from app.engines import scope as scope_engine
from app.engines import wbs as wbs_engine
from app.models.domain import (
    MaterialTier,
    MediaAsset,
    RenovationBrief,
    Scenario,
    ScenarioKind,
    ScopeSummary,
    WBS,
)


@dataclass
class PipelineResult:
    scope: ScopeSummary
    wbs: WBS
    scenarios: list[Scenario]
    selected: ScenarioKind
    missing_price_codes: list[str] = field(default_factory=list)

    def to_brief(self, title: str) -> RenovationBrief:
        return RenovationBrief(
            project_title=title,
            scope=self.scope,
            wbs=self.wbs,
            scenarios=self.scenarios,
            selected=self.selected,
        )


def run(
    *,
    description: str,
    total_area_m2: float | None = None,
    assets: list[MediaAsset] | None = None,
    vision_analyzer=None,
    tier: MaterialTier = MaterialTier.STANDARD,
) -> PipelineResult:
    """اجرای کامل pipeline: متن/رسانه → Scope → WBS → متریال → سناریوها."""
    scope = scope_engine.analyze_with_vision(
        assets or [], description, analyzer=vision_analyzer, total_area_m2=total_area_m2
    )
    wbs = wbs_engine.generate(scope)
    priced, missing = material_engine.apply(wbs, tier)
    scenarios = scenario_engine.build_all(priced)

    return PipelineResult(
        scope=scope,
        wbs=priced,
        scenarios=scenarios,
        selected=scenario_engine.nearest_to_budget(scenarios, scope.budget_toman),
        missing_price_codes=missing,
    )


def render_brief(result: PipelineResult, title: str) -> str:
    return brief_engine.render(result.to_brief(title))


def run_to_file(
    *,
    description: str,
    output_path: Path,
    title: str,
    total_area_m2: float | None = None,
    assets: list[MediaAsset] | None = None,
    vision_analyzer=None,
) -> PipelineResult:
    result = run(
        description=description,
        total_area_m2=total_area_m2,
        assets=assets,
        vision_analyzer=vision_analyzer,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_brief(result, title), encoding="utf-8")
    return result
