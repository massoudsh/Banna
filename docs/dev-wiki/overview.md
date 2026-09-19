# Overview — بنّا (Banna)

کوپایلوت هوشمند برنامه‌ریزی و اجرای بازسازی برای بازار ایران. جزئیات محصول/مسئله/مدل کسب‌وکار در [[../../README.md|README]] و `docs/wiki/` (ویکی محصول).

## وضعیت فعلی کد
فاز ۱ (Scope & Estimate Copilot) **پیاده‌سازی‌شده** است — موتورهای قاعده‌محور،
قطعی و بدون نیاز به شبکه، با ۱۹۶ تست. لایهٔ HTTP/UI هم ساخته شده: آپلود →
پردازش → نمایش چهار سناریو → دانلود Brief.

## پشتهٔ فنی
Python 3.11+ · Pydantic v2 (مدل داده) · FastAPI + uvicorn (لایهٔ HTTP) · pytest.
ذخیره‌سازی در MVP **در حافظه** است؛ مهاجرت به SQLite/Postgres پیش از استقرار
لازم است (تصمیم قفل‌شده: `../specs/architecture.md`).

## پوشه‌بندی
```
app/models/domain.py    قرارداد داده بین موتورها (تنها منبع مجاز تبادل)
app/engines/            هفت موتور: media, scope, wbs, material, estimate, scenario, brief
app/pipeline.py         orchestrator زنجیره
app/api/                لایهٔ FastAPI: main.py (routeها) + schemas.py + ui.py (صفحهٔ UI)
app/cli.py              ورودی خط فرمان (banna-brief)
data/                   wbs_reference.json + price_dataset.json
tests/                  ۱۹۶ تست، بدون تماس شبکه
docs/specs/             معماری، WBS مرجع، دیتاست قیمت، قفل دامنه، UI، تست پذیرش، مصاحبه
```

## اجرای سرویس
```
uvicorn app.api.main:app
```

## زنجیرهٔ فاز ۱
`analyze_with_vision → wbs.generate → material.apply → scenario.build_all → brief.render`

هر مرحله خروجی ساختاریافته می‌دهد، پس می‌توان در میانهٔ زنجیره متوقف و از همان
نقطه ادامه داد (لازمهٔ خروجی قابل‌ویرایش — Issue #7). جزئیات: [[entities/pipeline]].

## اصل عرضی: عدم‌قطعیت
هزینه و زمان همیشه **بازه** هستند، فرض‌ها صریح اعلام می‌شوند، و دادهٔ ناقص
بی‌صدا حذف نمی‌شود. جزئیات: [[concepts/uncertainty-model]].

## Next.js MVP surface
یک سطح Next.js مستقل نیز برای دریافت ورودی پروژه، نمایش scope، WBS، متریال، تخمین و چهار سناریو اضافه شده است:
- `app/page.tsx` — صفحهٔ خانه و CTAهای ورودی پروژه
- `app/upload/page.tsx` — فرم آپلود و نمایش brief
- `app/api/scope/route.ts` — API اعتبارسنجی و fallback محلی
- `lib/project-intake.ts` — منطق Summary، WBS، تخمین و سناریوها
- `lib/pricing-sources.ts` — provenance منابع قیمت تهران

## نقشهٔ راه فنی (خلاصه)
- فاز ۱ — MVP ✅ پیاده‌سازی‌شده (بدون لایهٔ HTTP/UI).
- فاز ۲ — Contractor Matching & Quote Normalization.
- فاز ۳ — Execution Tracking.
- فاز ۴ — Escrow & Financing.

جزئیات کامل هر فاز: `../../ROADMAP.md`.

## قدم بعدی کد
لایهٔ FastAPI روی `app/pipeline.py` (آپلود فایل + اجرای زنجیره + دانلود Brief)،
سپس UI طبق `../specs/ui-flow.md`. معیار پذیرش فاز ۱ میدانی است:
`../specs/acceptance-testing.md`.
