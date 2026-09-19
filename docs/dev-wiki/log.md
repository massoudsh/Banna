# Log

## [2026-08-16] update | راه‌اندازی دانش‌نامهٔ توسعه (dev-wiki) طبق قالب Vault Template؛ ریپو هنوز در مرحلهٔ planning-only است.
## [2026-08-16] update | اتصال GitHub برقرار شد: کامیت‌های محلی push شدند، Issue #17/#18 (فاز ۴) + لیبل `phase-4` + مایلستون «فاز ۴» روی GitHub ساخته شد، و `docs/wiki/*.md` با GitHub Wiki واقعی مخزن sync شد.
## [2026-09-19] update | پیاده‌سازی فاز ۱ (Issueهای #5–#11): هفت موتور (`app/engines/`) + `app/models/domain.py` + `app/pipeline.py` + CLI، دیتاست‌های `data/wbs_reference.json` و `data/price_dataset.json`، ۱۶۳ تست، و `docs/specs/` (معماری، WBS مرجع، دیتاست قیمت، قفل دامنهٔ MVP، جریان UI، تست پذیرش، مصاحبه). تغییرات رفتاری مهم: `_normalize_area()` در scope، `FULL_SCOPE_KEYWORDS` برای «بازسازی کامل»، `TIER_SPEED` در estimate، و `_select()` در pipeline (بودجه بر tier اولویت دارد).
