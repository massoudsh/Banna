import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="min-h-screen bg-stone-50 text-stone-900">
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="rounded-3xl border border-stone-200 bg-white p-8 shadow-sm">
          <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-brand-600">
            Banna
          </p>
          <h1 className="text-4xl font-black md:text-6xl">کوپایلوت برنامه‌ریزی بازسازی</h1>
          <p className="mt-6 max-w-2xl text-lg text-stone-600">
            از آپلود عکس و ویدیو تا استخراج scope، پیشنهاد متریال، تولید WBS و تخمین هزینه و زمان.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/upload"
              className="rounded-xl bg-brand-600 px-5 py-3 font-bold text-white transition hover:bg-brand-700"
            >
              شروع پروژه جدید
            </Link>
            <Link
              href="/upload"
              className="rounded-xl border border-stone-300 bg-stone-50 px-5 py-3 font-bold text-stone-800 transition hover:border-stone-400"
            >
              مشاهده فرم آپلود
            </Link>
          </div>

          <div className="mt-10 grid gap-5 md:grid-cols-3">
            <div className="rounded-2xl bg-brand-50 p-5">
              <h2 className="font-bold text-brand-700">۱. آپلود پروژه</h2>
              <p className="mt-2 text-sm text-stone-700">عکس، ویدیو و توضیح متنی پروژه را وارد کنید.</p>
            </div>
            <div className="rounded-2xl bg-stone-100 p-5">
              <h2 className="font-bold text-stone-800">۲. استخراج Scope</h2>
              <p className="mt-2 text-sm text-stone-700">AI فضاها، نیازها و سطح پروژه را تشخیص می‌دهد.</p>
            </div>
            <div className="rounded-2xl bg-stone-100 p-5">
              <h2 className="font-bold text-stone-800">۳. Brief آماده</h2>
              <p className="mt-2 text-sm text-stone-700">WBS، متریال، زمان و سناریوهای هزینه آماده می‌شود.</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
