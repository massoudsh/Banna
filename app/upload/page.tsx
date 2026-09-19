"use client";

import Link from 'next/link';
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';

import type { ProjectSummary } from '@/lib/project-intake';

const MAX_FILE_SIZE_MB = 25;
const SAVED_PROJECT_KEY = 'banna:last-project';

export default function UploadPage() {
  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [budget, setBudget] = useState('');
  const [surfaceArea, setSurfaceArea] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState('');
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const savedProject = window.localStorage.getItem(SAVED_PROJECT_KEY);
    if (!savedProject) return;

    try {
      const saved = JSON.parse(savedProject) as {
        projectName: string;
        description: string;
        budget: string;
        surfaceArea: string;
        summary: ProjectSummary;
      };
      setProjectName(saved.projectName);
      setDescription(saved.description);
      setBudget(saved.budget);
      setSurfaceArea(saved.surfaceArea);
      setSummary(saved.summary);
    } catch {
      window.localStorage.removeItem(SAVED_PROJECT_KEY);
    }
  }, []);

  const fileSummary = useMemo(
    () =>
      files.length
        ? files.map((file) => `${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`).join(', ')
        : 'هیچ فایلی انتخاب نشده',
    [files],
  );

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []);
    const invalid = selected.find((file) => file.size > MAX_FILE_SIZE_MB * 1024 * 1024);

    if (invalid) {
      setError(`حجم ${invalid.name} بیشتر از ${MAX_FILE_SIZE_MB}MB است.`);
      setFiles([]);
      return;
    }

    setError('');
    setFiles(selected);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!projectName.trim()) {
      setError('لطفاً نام پروژه را وارد کنید.');
      return;
    }

    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/scope', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectName,
          description,
          budget,
          surfaceArea,
          fileCount: files.length,
          fileNames: files.map((file) => file.name),
        }),
      });

      if (!response.ok) throw new Error('scope request failed');

      const generatedSummary = (await response.json()) as ProjectSummary;
      setSummary(generatedSummary);
      window.localStorage.setItem(
        SAVED_PROJECT_KEY,
        JSON.stringify({ projectName, description, budget, surfaceArea, summary: generatedSummary }),
      );
    } catch {
      setError('پردازش پروژه انجام نشد. لطفاً دوباره تلاش کنید.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="mb-6">
        <Link href="/" className="text-sm font-medium text-brand-600 hover:text-brand-700">
          ← بازگشت به خانه
        </Link>
      </div>

      <div className="rounded-3xl border border-stone-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-brand-600">Phase 1</p>
        <h1 className="mt-3 text-3xl font-black text-stone-900">آپلود و پردازش پروژه</h1>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div>
            <label className="mb-2 block text-sm font-semibold text-stone-700">نام پروژه</label>
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full rounded-xl border border-stone-300 px-4 py-3 outline-none ring-0 focus:border-brand-500"
              placeholder="مثلاً: آپارتمان دو خواب در تهران"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-stone-700">توضیح کوتاه پروژه</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              className="w-full rounded-xl border border-stone-300 px-4 py-3 outline-none focus:border-brand-500"
              placeholder="موقعیت، وضعیت فعلی، نیازهای اصلی، سبک موردنظر و مشکلات فعلی را بنویسید..."
            />
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-stone-700">بودجه پیشنهادی (تومان)</label>
              <input
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="w-full rounded-xl border border-stone-300 px-4 py-3 outline-none focus:border-brand-500"
                placeholder="مثلاً: 850000000"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-stone-700">متراژ (متر مربع)</label>
              <input
                value={surfaceArea}
                onChange={(e) => setSurfaceArea(e.target.value)}
                className="w-full rounded-xl border border-stone-300 px-4 py-3 outline-none focus:border-brand-500"
                placeholder="مثلاً: 120"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-stone-700">آپلود عکس و ویدیو</label>
            <input
              type="file"
              multiple
              accept="image/*,video/*"
              onChange={handleFileChange}
              className="w-full rounded-xl border border-dashed border-stone-300 bg-stone-50 px-4 py-6 text-sm text-stone-700"
            />
            <p className="mt-2 text-xs text-stone-500">حداکثر حجم هر فایل: {MAX_FILE_SIZE_MB}MB</p>
            <p className="mt-3 text-sm text-stone-700">{fileSummary}</p>
          </div>

          {error ? <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-xl bg-brand-600 px-6 py-3 font-bold text-white transition hover:bg-brand-700"
          >
            {isSubmitting ? 'در حال پردازش...' : 'ثبت ورودی پروژه'}
          </button>
        </form>

        {summary ? (
          <div className="mt-10 rounded-2xl border border-brand-200 bg-brand-50 p-6">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-brand-600">Scope Preview</p>
            <h2 className="mt-3 text-2xl font-black text-stone-900">{summary.title}</h2>
            <p className="mt-2 text-xs text-stone-500">
              {summary.source === 'ai' ? 'تحلیل‌شده با AI' : 'پیش‌نمایش محلی؛ آماده اتصال به مدل AI'}
            </p>

            <div className="mt-5 grid gap-5 md:grid-cols-2">
              <div className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-stone-700">بازه بودجه</p>
                <p className="mt-2 text-lg font-black text-stone-900">{summary.budgetBand}</p>
              </div>
              <div className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-stone-700">تخمین اولیه</p>
                <p className="mt-2 text-lg font-black text-stone-900">{summary.estimatedRange}</p>
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-white p-4 shadow-sm">
              <p className="text-sm font-semibold text-stone-700">برآورد هزینه و زمان</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <div>
                  <p className="text-xs text-stone-500">کل هزینه</p>
                  <p className="mt-1 font-bold text-stone-900">{summary.estimate.totalCost}</p>
                </div>
                <div>
                  <p className="text-xs text-stone-500">مدت اجرا</p>
                  <p className="mt-1 font-bold text-stone-900">{summary.estimate.duration}</p>
                </div>
                <div>
                  <p className="text-xs text-stone-500">عدم قطعیت</p>
                  <p className="mt-1 text-sm font-bold text-stone-900">{summary.estimate.uncertainty}</p>
                </div>
              </div>
              <p className="mt-4 text-xs leading-6 text-stone-500">
                منبع مبنا: {summary.estimate.pricingSource} · وضعیت: {summary.estimate.pricingStatus === 'provisional' ? 'نیازمند واردکردن نسخه رسمی و ضریب منطقه‌ای تهران' : 'کالیبره‌شده'}
              </p>
            </div>

            <div className="mt-6">
              <p className="text-sm font-semibold text-stone-700">سناریوهای پیشنهادی</p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {summary.scenarios.map((scenario) => (
                  <div key={scenario.name} className="rounded-2xl bg-white p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-bold text-stone-900">{scenario.name}</p>
                      <span className="rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700">{scenario.materialLevel}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-stone-600">{scenario.description}</p>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-xs text-stone-500">هزینه</p>
                        <p className="mt-1 font-semibold text-stone-800">{scenario.cost}</p>
                      </div>
                      <div>
                        <p className="text-xs text-stone-500">زمان</p>
                        <p className="mt-1 font-semibold text-stone-800">{scenario.duration}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <p className="text-sm font-semibold text-stone-700">Scope تشخیص داده‌شده</p>
              <ul className="mt-3 space-y-2 text-sm text-stone-700">
                {summary.scope.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="mt-1 inline-block h-2 w-2 rounded-full bg-brand-500" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-6">
              <p className="text-sm font-semibold text-stone-700">گام‌های بعدی</p>
              <ul className="mt-3 space-y-2 text-sm text-stone-700">
                {summary.nextSteps.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="mt-1 inline-block h-2 w-2 rounded-full bg-stone-500" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-6">
              <p className="text-sm font-semibold text-stone-700">ترتیب اجرای پیشنهادی (WBS)</p>
              <ol className="mt-3 grid gap-3 md:grid-cols-2">
                {summary.wbs.map((workPackage) => (
                  <li key={workPackage.order} className="rounded-2xl bg-white p-4 shadow-sm">
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-black text-brand-700">
                        {workPackage.order}
                      </span>
                      <p className="font-bold text-stone-900">{workPackage.phase}</p>
                    </div>
                    <ul className="mt-3 space-y-1 text-sm text-stone-600">
                      {workPackage.tasks.map((task) => (
                        <li key={task}>• {task}</li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            </div>

            <div className="mt-6 overflow-x-auto">
              <p className="text-sm font-semibold text-stone-700">تفکیک برآورد بر اساس WBS</p>
              <table className="mt-3 min-w-full text-right text-sm">
                <thead className="border-b border-stone-200 text-stone-500">
                  <tr>
                    <th className="px-3 py-2 font-semibold">مرحله</th>
                    <th className="px-3 py-2 font-semibold">هزینه</th>
                    <th className="px-3 py-2 font-semibold">زمان</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.estimate.lineItems.map((item) => (
                    <tr key={item.phase} className="border-b border-stone-100">
                      <td className="px-3 py-3 font-medium text-stone-800">{item.phase}</td>
                      <td className="px-3 py-3 text-stone-600">{item.cost}</td>
                      <td className="px-3 py-3 text-stone-600">{item.duration}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6">
              <p className="text-sm font-semibold text-stone-700">پیشنهاد اولیه متریال</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {summary.materials.map((material) => (
                  <div key={material.category} className="rounded-2xl bg-white p-4 shadow-sm">
                    <p className="text-xs font-semibold text-brand-600">{material.category}</p>
                    <p className="mt-2 font-bold text-stone-900">{material.suggestion}</p>
                    <p className="mt-2 text-sm leading-6 text-stone-600">{material.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}

