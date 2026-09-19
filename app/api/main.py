"""FastAPI بنّا — جریان آپلود تا دریافت Brief (Issue #5 تا #12).

اجرای موقت برای تست:
    uvicorn app.api.main:app

نکته: این سرویس پردازش را **در حافظه** نگه می‌دارد (MVP بدون دیتابیس). برای
استقرار واقعی، `_PROJECTS` باید به SQLite/Postgres منتقل شود.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from app.api import ui
from app.api.schemas import (
    CostRangeOut,
    ProjectOut,
    ScenarioOut,
    SpaceOut,
    WBSItemOut,
)
from app.engines import brief as brief_engine
from app.engines import quote as quote_engine
from app.engines import contractor as contractor_engine
from app.engines.media import MediaValidationError, store_asset, validate_request
from app.engines.scope import ScopeError
from app.engines.wbs import WBSError
from app.models.domain import (
    PHASE_LABELS_FA,
    SCENARIO_LABELS_FA,
    WorkPhase,
    ContractorQuote,
    QuoteComparison,
    SpaceType,
    ContractorProfile,
    ContractorReview,
    ContractorRanking,
    ProjectExecutionChecklist,
    ChecklistItem,
)
from app.pipeline import PipelineResult, run

# مسیرهای ذخیره‌سازی — بیرون از کد، در ریشهٔ پروژه
BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "uploads" / "media"

MIN_AREA_M2 = 20
MAX_AREA_M2 = 1000

SPACE_LABELS_FA: dict[SpaceType, str] = {
    SpaceType.KITCHEN: "آشپزخانه",
    SpaceType.BATHROOM: "حمام و سرویس",
    SpaceType.LIVING_ROOM: "نشیمن و پذیرایی",
    SpaceType.BEDROOM: "اتاق خواب",
}

CONDITION_LABELS_FA = {"good": "سالم", "fair": "متوسط", "poor": "فرسوده"}

app = FastAPI(
    title="بنّا — کوپایلوت برنامه‌ریزی بازسازی",
    description="از ورودی چندرسانه‌ای کارفرما تا Brief قابل‌اشتراک با مجری.",
    version="0.1.0",
)

app.include_router(ui.router)

# حافظهٔ موقت پروژه‌ها (MVP). کلید: project_id
_PROJECTS: dict[str, PipelineResult] = {}
_TITLES: dict[str, str] = {}
_QUOTES: dict[str, list[ContractorQuote]] = {}
_CONTRACTORS: dict[str, ContractorProfile] = {}
_REVIEWS: list[ContractorReview] = []
_CHECKLISTS: dict[str, ProjectExecutionChecklist] = {}


@app.exception_handler(MediaValidationError)
async def _media_error_handler(_request, exc: MediaValidationError) -> JSONResponse:
    """خطای ورودی نامعتبر → ۴۰۰ با پیام فارسی قابل‌نمایش."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ScopeError)
async def _scope_error_handler(_request, exc: ScopeError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(WBSError)
async def _wbs_error_handler(_request, exc: WBSError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/projects", response_model=ProjectOut, status_code=201)
async def create_project(
    description: str = Form(..., min_length=1),
    total_area_m2: float | None = Form(default=None),
    title: str = Form(default="پروژهٔ بازسازی"),
    files: list[UploadFile] = File(default=[]),
) -> ProjectOut:
    """اجرای زنجیرهٔ کامل از ورودی کاربر و بازگرداندن خروجی ساختاریافته.

    اعتبارسنجی پیش از پردازش انجام می‌شود تا فایل نامعتبر اصلاً ذخیره نشود.
    """
    if total_area_m2 is not None and not (MIN_AREA_M2 <= total_area_m2 <= MAX_AREA_M2):
        raise HTTPException(
            status_code=400,
            detail=(
                "متراژ باید بین ۲۰ و ۱۰۰۰ مترمربع باشد "
                f"(مقدار داده‌شده: {total_area_m2:g})."
            ),
        )

    # فایل‌های آپلودی که واقعاً محتوا دارند (فرم خالی فیلد files می‌فرستد)
    real_files = [f for f in files if f.filename]

    try:
        validate_request(
            area_m2=total_area_m2,
            media_count=len(real_files),
            description=description,
        )
    except MediaValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    project_id = uuid.uuid4().hex[:12]
    assets = []
    for upload in real_files:
        content = await upload.read()
        # پسوند اصلی فایل حفظ می‌شود؛ اعتبارسنجی `store_asset` به آن وابسته است.
        suffix = Path(upload.filename or "").suffix.lower()
        tmp = STORAGE_DIR / f".incoming-{uuid.uuid4().hex}{suffix}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(content)
        try:
            asset = store_asset(
                tmp,
                f"{project_id}-{len(assets)}",
                STORAGE_DIR,
                content_type=upload.content_type or "application/octet-stream",
            )
        finally:
            tmp.unlink(missing_ok=True)
        # نام اصلی فایل کاربر برای پیام خطای بعدی حفظ می‌شود
        assets.append(asset.model_copy(update={"filename": upload.filename}))

    try:
        result = run(
            description=description,
            total_area_m2=total_area_m2,
            assets=assets,
        )
    except (ScopeError, WBSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _PROJECTS[project_id] = result
    _TITLES[project_id] = title
    return _to_out(project_id, result, title)


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str) -> ProjectOut:
    result = _PROJECTS.get(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد.")
    return _to_out(project_id, result, _TITLES.get(project_id, "پروژهٔ بازسازی"))


@app.get("/api/projects/{project_id}/quotes", response_model=QuoteComparison)
async def get_quote_comparison(project_id: str) -> QuoteComparison:
    """مقایسهٔ quoteهای ثبت‌شده با سناریوی انتخابی پروژه."""
    result = _PROJECTS.get(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد.")
    quotes = _QUOTES.get(project_id, [])
    if not quotes:
        raise HTTPException(status_code=404, detail="هنوز quoteی برای این پروژه ثبت نشده است.")
    baseline = quote_engine.baseline_for(result.scenarios, result.selected)
    return quote_engine.compare(quotes, result.wbs, baseline)


@app.post("/api/projects/{project_id}/quotes", response_model=QuoteComparison, status_code=201)
async def add_contractor_quote(project_id: str, quote: ContractorQuote) -> QuoteComparison:
    """ثبت quote یک مجری و بازگرداندن مقایسهٔ به‌روز با WBS."""
    result = _PROJECTS.get(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد.")
    project_quotes = _QUOTES.setdefault(project_id, [])
    project_quotes[:] = [q for q in project_quotes if q.contractor_id != quote.contractor_id]
    project_quotes.append(quote)
    baseline = quote_engine.baseline_for(result.scenarios, result.selected)
    return quote_engine.compare(project_quotes, result.wbs, baseline)


@app.post("/api/contractors", response_model=ContractorProfile, status_code=201)
async def create_contractor(profile: ContractorProfile) -> ContractorProfile:
    _CONTRACTORS[profile.contractor_id] = profile
    return profile


@app.post("/api/contractors/{contractor_id}/reviews", response_model=ContractorReview, status_code=201)
async def add_contractor_review(contractor_id: str, review: ContractorReview) -> ContractorReview:
    if contractor_id not in _CONTRACTORS or review.contractor_id != contractor_id:
        raise HTTPException(status_code=404, detail="مجری پیدا نشد.")
    _REVIEWS.append(review)
    return review


@app.get("/api/contractors/ranking", response_model=list[ContractorRanking])
async def get_contractor_ranking() -> list[ContractorRanking]:
    return contractor_engine.rank(list(_CONTRACTORS.values()), _REVIEWS)


@app.get("/api/projects/{project_id}/checklist", response_model=ProjectExecutionChecklist)
async def get_checklist(project_id: str) -> ProjectExecutionChecklist:
    result = _PROJECTS.get(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد.")
    return _CHECKLISTS.setdefault(
        project_id,
        ProjectExecutionChecklist(
            project_id=project_id,
            items=[ChecklistItem(wbs_code=item.code) for item in result.wbs.ordered()],
        ),
    )


@app.put("/api/projects/{project_id}/checklist", response_model=ProjectExecutionChecklist)
async def update_checklist(project_id: str, checklist: ProjectExecutionChecklist) -> ProjectExecutionChecklist:
    result = _PROJECTS.get(project_id)
    if result is None or checklist.project_id != project_id:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد.")
    valid_codes = {item.code for item in result.wbs.items}
    if any(item.wbs_code not in valid_codes for item in checklist.items):
        raise HTTPException(status_code=422, detail="چک‌لیست شامل کد WBS ناشناخته است.")
    _CHECKLISTS[project_id] = checklist
    return checklist


@app.get("/api/projects/{project_id}/brief", response_class=HTMLResponse)
async def get_brief(project_id: str) -> HTMLResponse:
    """Brief نهایی به‌صورت HTML فارسی/RTL — آمادهٔ چاپ یا تبدیل به PDF."""
    result = _PROJECTS.get(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="پروژه پیدا نشد.")
    quotes = _QUOTES.get(project_id, [])
    comparison = None
    if quotes:
        baseline = quote_engine.baseline_for(result.scenarios, result.selected)
        comparison = quote_engine.compare(quotes, result.wbs, baseline)
    html = brief_engine.render(
        result.to_brief(_TITLES.get(project_id, "پروژهٔ بازسازی")),
        comparison,
    )
    return HTMLResponse(content=html)


def _to_out(project_id: str, result: PipelineResult, title: str) -> ProjectOut:
    """تبدیل PipelineResult به مدل HTTP — منطق نمایش در یک جا."""
    return ProjectOut(
        project_id=project_id,
        title=title,
        total_area_m2=result.scope.total_area_m2,
        style=result.scope.style,
        budget_toman=result.scope.budget_toman,
        spaces=[
            SpaceOut(
                space=s.space.value,
                label_fa=SPACE_LABELS_FA[s.space],
                area_m2=s.area_m2,
                condition=CONDITION_LABELS_FA[s.condition.value],
                confidence=s.confidence,
                requested_works=[PHASE_LABELS_FA[w] for w in s.requested_works],
            )
            for s in result.scope.spaces
        ],
        scenarios=[
            ScenarioOut(
                kind=sc.kind.value,
                label_fa=SCENARIO_LABELS_FA[sc.kind],
                tier=sc.tier.value,
                description=sc.description,
                cost=CostRangeOut(
                    min_toman=sc.estimate.cost_min_toman,
                    max_toman=sc.estimate.cost_max_toman,
                ),
                duration_days=CostRangeOut(
                    min_toman=sc.estimate.duration_days_min,
                    max_toman=sc.estimate.duration_days_max,
                ),
            )
            for sc in result.scenarios
        ],
        selected=result.selected.value,
        wbs_items=[
            WBSItemOut(
                code=i.code,
                title=i.title,
                phase=i.phase.value,
                phase_label_fa=PHASE_LABELS_FA[i.phase],
                space=SPACE_LABELS_FA[i.space],
                quantity=i.quantity,
                unit=i.unit,
                material=i.materials[0].name if i.materials else None,
                depends_on=i.depends_on,
            )
            for i in result.wbs.ordered()
        ],
        assumptions=result.scope.assumptions,
        missing_price_codes=result.missing_price_codes,
        brief_url=f"/api/projects/{project_id}/brief",
    )


# اطمینان از این‌که فازها در OpenAPI هم دیده شوند (مستندسازی برای مصرف‌کننده)
assert set(PHASE_LABELS_FA) == set(WorkPhase)
