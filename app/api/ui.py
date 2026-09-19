"""صفحهٔ تک‌فایلی UI — جریان آپلود تا دریافت Brief (Issue #12).

پیاده‌سازی سبک از طراحی `docs/specs/ui-flow.md`: بدون build tool، بدون
فریم‌ورک؛ همان رعایت قواعد UX (بازه به‌جای عدد قطعی، فرض‌های قابل‌مشاهده،
پیام خطای فارسی، RTL کامل).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>بنّا — قبل از شروع، پروژه‌ت رو بفهم</title>
<style>
  :root { --green:#2f6f4e; --bg:#f7f7f8; --line:#e2e2e6; --warn:#a12626; }
  * { box-sizing: border-box; }
  body { font-family:"IRANSans",Tahoma,sans-serif; background:var(--bg); color:#1a1a1a;
         line-height:1.9; margin:0; padding:2rem 1rem; }
  .wrap { max-width:960px; margin:auto; }
  h1 { font-size:1.5rem; border-bottom:3px solid var(--green); padding-bottom:.5rem; }
  h2 { font-size:1.1rem; color:var(--green); margin-top:2rem; }
  .tag { color:#666; font-size:.9rem; margin-top:-.5rem; }
  form, .card { background:#fff; border:1px solid var(--line); border-radius:10px;
                padding:1.25rem; margin-top:1rem; }
  label { display:block; font-size:.9rem; margin:.75rem 0 .25rem; font-weight:bold; }
  input, textarea { width:100%; padding:.6rem; border:1px solid var(--line);
                    border-radius:6px; font-family:inherit; font-size:.95rem; }
  textarea { min-height:80px; resize:vertical; }
  button { background:var(--green); color:#fff; border:0; border-radius:6px;
           padding:.7rem 1.5rem; font-family:inherit; font-size:1rem; cursor:pointer;
           margin-top:1rem; }
  button:disabled { opacity:.55; cursor:wait; }
  button.alt { background:#5a6570; padding:.45rem 1rem; font-size:.9rem; margin:0; }
  .hint { font-size:.8rem; color:#777; margin-top:.2rem; }
  table { width:100%; border-collapse:collapse; background:#fff; margin-top:.75rem; }
  th,td { border:1px solid var(--line); padding:.5rem .65rem; text-align:right;
          font-size:.9rem; }
  th { background:#eef4f0; }
  .grid { display:grid; gap:1rem; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
          margin-top:1rem; }
  .scen { border:2px solid var(--line); border-radius:10px; padding:1rem; background:#fff; }
  .scen.sel { border-color:var(--green); box-shadow:0 0 0 3px #e3f3e9; }
  .scen .price { font-size:1.15rem; font-weight:bold; color:var(--green); }
  .badge { background:#e3f3e9; color:#22603f; border-radius:4px; padding:.1rem .4rem;
           font-size:.75rem; }
  .badge.warn { background:#fdecec; color:var(--warn); }
  .err { background:#fdecec; color:var(--warn); border:1px solid #f5c2c2;
         border-radius:6px; padding:.75rem; margin-top:1rem; }
  .assumptions { color:#666; font-size:.85rem; }
  .steps { display:flex; gap:.5rem; font-size:.85rem; color:#888; margin-top:1rem;
           flex-wrap:wrap; }
  .steps span.on { color:var(--green); font-weight:bold; }
  .hidden { display:none; }
  a { color:var(--green); }
</style>
</head>
<body>
<div class="wrap">
  <h1>بنّا</h1>
  <p class="tag">قبل از شروع، پروژه‌ت رو بفهم — تخمین شفاف بازسازی از روی عکس و توضیح شما.</p>

  <div class="steps" id="steps">
    <span id="s1" class="on">۱. ورودی</span><span>←</span>
    <span id="s2">۲. پردازش</span><span>←</span>
    <span id="s3">۳. سناریوها</span><span>←</span>
    <span id="s4">۴. بریف</span>
  </div>

  <form id="form">
    <label for="area">متراژ تقریبی (مترمربع)</label>
    <input id="area" name="area" type="number" min="20" max="1000" step="0.5" placeholder="۸۰">
    <div class="hint">بین ۲۰ تا ۱۰۰۰ مترمربع. اگه نمی‌دونی، خالی بذار.</div>

    <label for="desc">توضیح پروژه <span style="color:#a12626">*</span></label>
    <textarea id="desc" name="desc" required
      placeholder="مثلاً: آشپزخانه و حمام قدیمیه، کابینت و کاشی عوض بشه، بودجه ۵۰۰ میلیون تومان"></textarea>
    <div class="hint">بودجه و متراژ را در همین متن هم می‌توانید بنویسید.</div>

    <label for="files">عکس یا ویدیوی فضا</label>
    <input id="files" name="files" type="file" multiple
           accept="image/jpeg,image/png,image/webp,image/heic,video/mp4,video/quicktime,video/webm">
    <div class="hint">حداکثر ۲۵ مگابایت هر فایل. فعلاً تحلیل متنی فعال است؛ عکس‌ها ذخیره می‌شوند.</div>

    <button type="submit" id="submit">ساخت برنامهٔ بازسازی</button>
    <div id="error"></div>
  </form>

  <div id="results" class="hidden">
    <h2>وضعیت فضاها</h2>
    <div id="spaces"></div>

    <h2>مقایسهٔ سناریوها</h2>
    <div class="grid" id="scenarios"></div>

    <h2>فهرست کارها (WBS) با ترتیب اجرا</h2>
    <div id="wbs"></div>

    <div id="assumptions-box"></div>

    <h2>بریف نهایی</h2>
    <p><a id="brief-link" href="#" target="_blank">مشاهدهٔ سند قابل‌اشتراک با مجری</a></p>
  </div>
</div>

<script>
const fmt = n => {
  if (n >= 1e9) return (n/1e9).toFixed(2).replace(/\\.?0+$/,"") + " میلیارد تومان";
  return Math.round(n/1e6).toLocaleString("fa-IR") + " میلیون تومان";
};
const esc = s => String(s).replace(/[&<>"']/g, c => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const setStep = id => {
  ["s1","s2","s3","s4"].forEach(s => document.getElementById(s).classList.remove("on"));
  document.getElementById(id).classList.add("on");
};

document.getElementById("form").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = document.getElementById("submit");
  const errBox = document.getElementById("error");
  errBox.innerHTML = "";
  btn.disabled = true;
  btn.textContent = "در حال پردازش…";
  setStep("s2");

  const fd = new FormData();
  fd.append("description", document.getElementById("desc").value);
  const area = document.getElementById("area").value;
  if (area) fd.append("total_area_m2", area);
  for (const f of document.getElementById("files").files) fd.append("files", f);

  try {
    const res = await fetch("/api/projects", { method:"POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "خطای نامشخص در پردازش.");
    render(data);
    setStep("s4");
  } catch (err) {
    errBox.innerHTML = '<div class="err">' + esc(err.message) + '</div>';
    setStep("s1");
  } finally {
    btn.disabled = false;
    btn.textContent = "ساخت برنامهٔ بازسازی";
  }
});

function render(d) {
  document.getElementById("results").classList.remove("hidden");

  document.getElementById("spaces").innerHTML = `<table>
    <tr><th>فضا</th><th>متراژ</th><th>وضعیت فعلی</th><th>کارهای موردنیاز</th><th>اطمینان</th></tr>
    ${d.spaces.map(s => `<tr>
      <td>${esc(s.label_fa)}</td><td>${s.area_m2} مترمربع</td><td>${esc(s.condition)}</td>
      <td>${s.requested_works.map(esc).join("، ")}</td>
      <td>${Math.round(s.confidence*100)}٪</td></tr>`).join("")}
  </table>`;

  const budget = d.budget_toman;
  document.getElementById("scenarios").innerHTML = d.scenarios.map(s => {
    const inBudget = budget && s.cost.min_toman <= budget;
    const badge = !budget ? "" : (inBudget
      ? '<span class="badge">در بودجه</span>'
      : '<span class="badge warn">بالاتر از بودجه</span>');
    return `<div class="scen ${s.kind === d.selected ? "sel" : ""}">
      <div><strong>${esc(s.label_fa)}</strong> ${badge}</div>
      <div class="price">${fmt(s.cost.min_toman)} تا ${fmt(s.cost.max_toman)}</div>
      <div>مدت: ${s.duration_days.min_toman} تا ${s.duration_days.max_toman} روز</div>
      <div class="hint">${esc(s.description)}</div>
    </div>`;
  }).join("");

  document.getElementById("wbs").innerHTML = `<table>
    <tr><th>فاز</th><th>فضا</th><th>شرح کار</th><th>مقدار</th><th>متریال پیشنهادی</th></tr>
    ${d.wbs_items.map(i => `<tr>
      <td>${esc(i.phase_label_fa)}</td><td>${esc(i.space)}</td><td>${esc(i.title)}</td>
      <td>${i.quantity} ${esc(i.unit)}</td><td>${esc(i.material || "—")}</td></tr>`).join("")}
  </table>`;

  let extra = "";
  if (d.assumptions.length) {
    extra += `<h2>فرض‌ها و محدودیت‌ها</h2><ul class="assumptions">` +
      d.assumptions.map(a => `<li>${esc(a)}</li>`).join("") + `</ul>`;
  }
  if (d.missing_price_codes.length) {
    extra += `<div class="err">${d.missing_price_codes.length} آیتم بدون قیمت در دیتاست بود و از تخمین حذف شد.</div>`;
  }
  document.getElementById("assumptions-box").innerHTML = extra;

  document.getElementById("brief-link").href = d.brief_url;
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index() -> HTMLResponse:
    return HTMLResponse(content=PAGE)
