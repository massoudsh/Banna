# Pipeline — زنجیرهٔ تولید Brief

منبع: `app/pipeline.py`

## چیست
Orchestrator فاز ۱. ورودی خام کاربر را از هفت موتور عبور می‌دهد و به Brief نهایی
می‌رساند. هر مرحله خروجی ساختاریافته می‌دهد، بنابراین می‌توان در میانهٔ زنجیره
متوقف شد و از همان نقطه ادامه داد.

```
analyze_with_vision → wbs.generate → material.apply → scenario.build_all → brief.render
```

## امضاها
| تابع | ورودی | خروجی |
|---|---|---|
| `run(*, description, total_area_m2=None, assets=None, vision_analyzer=None, tier=STANDARD)` | متن/رسانه | `PipelineResult` |
| `render_brief(result, title)` | `PipelineResult` + عنوان | HTML |
| `run_to_file(*, description, output_path, title, ...)` | مسیر خروجی | `PipelineResult` (فایل هم می‌نویسد) |
| `_select(scenarios, budget_toman, tier)` | سناریوها + بودجه | `ScenarioKind` |

## نکات کلیدی
- **`tier` فقط سناریوی پیش‌فرض را انتخاب می‌کند**، نه متریال همهٔ سناریوها.
  `material.apply(wbs, tier)` فقط WBS پایه را پر می‌کند تا آیتم‌های بدون قیمت
  گزارش شوند؛ سپس `scenario.build_all()` هر سناریو را با سطح خودش از نو قیمت می‌زند.
- **بودجه بر `tier` اولویت دارد.** اگر بودجه اعلام شود، `nearest_to_budget` تصمیم می‌گیرد.
- `PipelineResult.missing_price_codes` آیتم‌های بدون ردیف قیمت را حمل می‌کند و
  تا انتها به سند می‌رسد (حذف بی‌صدا ممنوع).

## مرتبط
- [[entities/scope-engine]] [[entities/wbs-engine]] [[entities/estimate-engine]] [[entities/brief-renderer]]
- [[concepts/uncertainty-model]]
