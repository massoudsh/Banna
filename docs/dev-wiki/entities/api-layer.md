# API Layer — FastAPI روی pipeline

منبع: `app/api/` — Issueهای #5 تا #12 (لایهٔ HTTP و UI)

## چیست
لایهٔ نازک HTTP روی `app/pipeline.py`. هیچ منطق دامنه‌ای اینجا نیست؛ فقط
اعتبارسنجی ورودی، تبدیل مدل، و نگاشت خطا به کد وضعیت.

| فایل | نقش |
|---|---|
| `app/api/main.py` | اپ FastAPI، routeها، exception handlerها |
| `app/api/schemas.py` | مدل‌های ورودی/خروجی HTTP |
| `app/api/ui.py` | صفحهٔ تک‌فایلی UI (HTML/CSS/JS درون‌خطی) |

## Routeها
| متد | مسیر | خروجی |
|---|---|---|
| GET | `/` | صفحهٔ UI فارسی/RTL |
| GET | `/health` | `{"status":"ok"}` |
| POST | `/api/projects` | ۲۰۱ + `ProjectOut` |
| GET | `/api/projects/{id}` | ۲۰۰ + `ProjectOut` |
| GET | `/api/projects/{id}/brief` | HTML سند قابل‌اشتراک |
| GET | `/openapi.json` | schema خودکار |

## نگاشت خطا به کد وضعیت
| خطا | وضعیت | چرا |
|---|---|---|
| `MediaValidationError` | ۴۰۰ | ورودی نامعتبر — کاربر باید اصلاح کند |
| متراژ خارج از ۲۰–۱۰۰۰ | ۴۰۰ | دامنهٔ MVP (`docs/specs/mvp-scope-lock.md`) |
| `ScopeError` / `WBSError` | ۴۲۲ | ورودی معتبر ولی قابل پردازش نیست |
| پروژهٔ ناموجود | ۴۰۴ | — |
| نبود `description` | ۴۲۲ (خود FastAPI) | فیلد الزامی |

همهٔ پیام‌های خطا **فارسی** هستند و مستقیماً قابل‌نمایش به کاربر.

## حالت ذخیره‌سازی
پروژه‌ها **در حافظه** (`_PROJECTS` دیکشنری) نگه داشته می‌شوند — MVP بدون
دیتابیس. با ری‌استارت سرویس پاک می‌شوند. برای استقرار واقعی باید به
SQLite/Postgres منتقل شود (نگاه کنید به بخش ۱ در `docs/specs/architecture.md`).

ذخیره‌سازی فایل: `uploads/media/` با کلید `{project_id}-{index}{suffix}`.
پسوند فایل اصلی حفظ می‌شود چون `store_asset` به آن اعتبارسنجی می‌کند.

## نکات پیاده‌سازی
- **رسانه و متراژ هر دو اختیاری‌اند.** `validate_request` فقط وقتی خطا می‌دهد
  که هیچ‌کدام از سه ورودی (رسانه، متراژ، توضیح) موجود نباشد. متن به‌تنهایی
  کافی است — این با UI و اسپک UI هم‌راستاست.
- فایل آپلودی پیش از ذخیره به یک فایل موقت با پسوند اصلی نوشته می‌شود، سپس
  `store_asset` آن را با نام امن منتقل می‌کند؛ نام فایل کاربر در مسیر اثر ندارد.
- خطاهای دامنه با exception handler سراسری به JSON فارسی تبدیل می‌شوند، پس
  routeها نیازی به try/except تکراری ندارند (به‌جز مواردی که کد وضعیت متفاوت
  می‌خواهند).

## اجرا
```
uvicorn app.api.main:app
```

## پوشش تست
`tests/test_api.py` — ۲۹ تست با `TestClient` (بدون سرور واقعی و بدون شبکه):
سلامت، UI، ساخت پروژه، ترتیب فازها در خروجی، خطاهای اعتبارسنجی (متراژ، نوع
فایل، حجم)، بازیابی پروژه، Brief، و تولید OpenAPI.

## مرتبط
- [[entities/pipeline]] · [[entities/media-pipeline]] · [[entities/brief-renderer]]
