# Material Engine — نگاشت WBS به متریال قیمت‌گذاری‌شده

منبع: `app/engines/material.py` · داده: `data/price_dataset.json` — Issue #8

## چیست
هر آیتم WBS را به یک `MaterialOption` بر اساس سطح کیفیت درخواستی متصل می‌کند و
بازهٔ دستمزد و بهره‌وری روزانهٔ آن آیتم را در اختیار موتور تخمین می‌گذارد.

## توابع
| تابع | خروجی |
|---|---|
| `load_dataset()` | محتوای `price_dataset.json` (lru_cache) |
| `_resolve_key(item, items)` | کلید دیتاست برای کد WBS |
| `options_for(item, tier, dataset)` | `list[MaterialOption]` |
| `apply(wbs, tier)` | `(WBS به‌روزشده, فهرست کدهای بدون قیمت)` |
| `labor_range(item)` | `(min, max)` دستمزد |
| `productivity(item)` | مقدار کار در روز |

## `_resolve_key()` — چرا لازم است
کد WBS به شکل `KIT-COV-T` است ولی دیتاست هم کلید فضایی دارد و هم کلید عمومی.
ترتیب تلاش: `item.code` → `{prefix}-{suffix}` → `suffix`. پیشوندها:
`{kitchen: KIT, bathroom: BAT, living_room: LIV, bedroom: BED}`.

## رفتار در نبود قیمت
`apply()` آیتم بدون قیمت را **حذف نمی‌کند**؛ کدش را در `missing` برمی‌گرداند و
این فهرست تا `PipelineResult.missing_price_codes` و سپس متن سند می‌رسد.
حذف بی‌صدا ممنوع است چون تخمین ناقص را کامل جلوه می‌دهد.

## ساختار دیتاست
هر ردیف: `title`، `material.tiers.{economy,standard,premium}.{name,min,max}`،
`labor.{min,max}`، `productivity_m2_per_day`. **هر سه سطح الزامی است** چون هر
سناریو یک سطح را کامل مصرف می‌کند.

تست‌های `tests/test_material.py` این قواعد را روی همهٔ ردیف‌ها بررسی می‌کنند
(`min <= max`، `min > 0`، `premium.min >= economy.min`، وجود labor و productivity)
به‌علاوهٔ پوشش کامل: `test_fills_materials_for_all_items` با `missing == []`.

جزئیات دیتاست و روش به‌روزرسانی: `docs/specs/price-dataset.md`.

## مرتبط
- [[entities/wbs-engine]] · [[entities/estimate-engine]] · [[entities/scenario-engine]]
