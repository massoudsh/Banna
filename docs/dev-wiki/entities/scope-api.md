# Scope API

مسیر `POST /api/scope` مرز سرویس پردازش ورودی پروژه است.

## قرارداد
بدنهٔ درخواست شامل `projectName`, `description`, `budget`, `surfaceArea`, `fileCount` و `fileNames` است. پاسخ یک `ProjectSummary` ساختاریافته شامل scope، WBS، متریال و برآورد اولیه است.

## وضعیت فعلی
مسیر ورودی را اعتبارسنجی می‌کند و تا زمان تنظیم provider و credential هوش مصنوعی، از `generateProjectSummary()` به‌عنوان fallback شفاف استفاده می‌کند. فیلد `source` در پاسخ مشخص می‌کند خروجی از `fallback` یا `ai` آمده است.

## فایل‌های مرتبط
- `app/api/scope/route.ts`
- `app/upload/page.tsx`
- `lib/project-intake.ts`