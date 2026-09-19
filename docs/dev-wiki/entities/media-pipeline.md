# Media Pipeline — دریافت و اعتبارسنجی ورودی چندرسانه‌ای

منبع: `app/engines/media.py` — Issue #5

## چیست
اولین گام زنجیره: دریافت عکس/ویدیوی فضا، اعتبارسنجی، و ذخیرهٔ امن. خروجی
`MediaAsset` است که موتور Scope مصرف می‌کند.

## ثابت‌ها
| ثابت | مقدار |
|---|---|
| `MAX_FILE_BYTES` | 25MB |
| `ALLOWED_IMAGE_TYPES` | image/jpeg, image/png, image/webp, image/heic |
| `ALLOWED_VIDEO_TYPES` | video/mp4, video/quicktime, video/webm |

## توابع
| تابع | نقش |
|---|---|
| `validate_upload(filename, content_type, size_bytes)` | اعتبارسنجی پیش از ذخیره |
| `store_asset(source, asset_id, storage_dir, *, content_type, estimate_video_frames=6)` | ذخیره + `MediaAsset` |
| `validate_request(*, area_m2, media_count)` | اعتبارسنجی فرم پروژه |

## ترتیب بررسی‌ها در `validate_upload` عمدی است
نوع فایل → خالی‌بودن → حجم → پسوند. نوع اول بررسی می‌شود تا فایل غیرمجاز
اصلاً بررسی حجم نشود.

## نکتهٔ امنیتی: نام فایل کاربر در مسیر ذخیره اثر ندارد
`store_asset` فایل را با نام `{asset_id}{suffix}` ذخیره می‌کند، **نه** نام
کاربر — دفاع در برابر path traversal و برخورد نام. نام اصلی فقط برای نمایش در
`MediaAsset.filename` نگه داشته می‌شود. رگرسیون:
`test_stored_name_ignores_user_filename`.

## اعتبارسنجی دامنهٔ MVP
`validate_request` متراژ ۲۰–۱۰۰۰ مترمربع و حداقل یک رسانه را الزام می‌کند
(منطق دامنه: `docs/specs/mvp-scope-lock.md`).

## محدودیت شناخته‌شده
استخراج فریم کلیدی واقعی از ویدیو در MVP انجام نمی‌شود؛ `frame_count` فقط
تعداد تقریبی برای مرحلهٔ تحلیل بصری است (وابسته به ffmpeg در محیط اجرا).

## مرتبط
- [[entities/scope-engine]] · [[entities/pipeline]]
