# Index — دانش‌نامهٔ توسعهٔ بنّا

## Overview
- [[overview]] — معماری فاز ۱، پشتهٔ فنی، پوشه‌بندی و قدم بعدی

## Entities (۹ صفحه)
- [[entities/api-layer]] — لایهٔ FastAPI (routeها، نگاشت خطا، صفحهٔ UI)
- [[entities/pipeline]] — orchestrator زنجیرهٔ Scope→WBS→Material→Estimate→Scenario→Brief
- [[entities/media-pipeline]] — دریافت/اعتبارسنجی/ذخیرهٔ امن ورودی چندرسانه‌ای (Issue #5)
- [[entities/scope-engine]] — استخراج Scope از متن و رسانه (Issue #6)
- [[entities/wbs-engine]] — تولید WBS با ترتیب فازها و وابستگی‌ها (Issue #7)
- [[entities/material-engine]] — نگاشت WBS به متریال قیمت‌گذاری‌شده (Issue #8)
- [[entities/estimate-engine]] — تخمین بازهٔ هزینه و زمان (Issue #9)
- [[entities/scenario-engine]] — چهار سناریوی خروجی (Issue #10)
- [[entities/brief-renderer]] — تولید HTML/PDF فارسی قابل‌اشتراک (Issue #11)

## Concepts (۱ صفحه)
- [[concepts/uncertainty-model]] — اصل «همیشه بازه، فرض صریح، بدون حذف بی‌صدا»

## Next.js MVP Entities
- [[entities/project-intake]] — فرم و مدل یا entity ورودی پروژه، شامل نام پروژه، توضیح، بودجه، متراژ و فایل‌ها
- [[entities/scope-api]] — مرز API پردازش scope و fallback محلی فعلی

## Next.js MVP Concepts
- [[concepts/brief-generation]] — منطق تبدیل ورودی پروژه به خلاصهٔ اولیهٔ scope و بودجه
- [[concepts/tehran-pricing]] — تفکیک منبع رسمی دستمزد/اجرای دولت از قیمت بازار متریال تهران

## مرتبط
- ویکی محصول (برای انسان/GitHub Wiki): `../wiki/Home.md`
- بک‌لاگ Issueها: `../issues/README.md`
- نقشهٔ راه: `../../ROADMAP.md`
