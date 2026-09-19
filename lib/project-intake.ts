import { activePricingSource } from './pricing-sources.ts';

export type ProjectIntakeInput = {
  projectName: string;
  description: string;
  budget: string;
  surfaceArea: string;
  fileCount: number;
  fileNames: string[];
};

export type ProjectSummary = {
  title: string;
  source: 'fallback' | 'ai';
  budgetBand: string;
  estimatedRange: string;
  estimate: ProjectEstimate;
  scenarios: ProjectScenario[];
  scope: string[];
  wbs: WorkPackage[];
  materials: MaterialSuggestion[];
  nextSteps: string[];
};

export type WorkPackage = {
  order: number;
  phase: string;
  tasks: string[];
};

export type MaterialSuggestion = {
  category: string;
  suggestion: string;
  reason: string;
};

export type ProjectEstimate = {
  totalCost: string;
  duration: string;
  uncertainty: string;
  pricingSource: string;
  pricingStatus: 'provisional' | 'calibrated';
  lineItems: EstimateLineItem[];
};

export type EstimateLineItem = {
  phase: string;
  cost: string;
  duration: string;
};

export type ProjectScenario = {
  name: string;
  description: string;
  cost: string;
  duration: string;
  materialLevel: string;
};

function parseNumber(value: string): number {
  const normalized = value.replace(/[^0-9]/g, '');
  return normalized ? Number(normalized) : 0;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('fa-IR').format(value) + ' تومان';
}

export function generateProjectSummary(input: ProjectIntakeInput): ProjectSummary {
  const title = input.projectName.trim() || 'پروژه جدید';
  const budgetValue = parseNumber(input.budget);
  const areaValue = parseNumber(input.surfaceArea);
  const descriptionText = (input.description || '').trim();
  const fileLabel = input.fileCount > 0 ? `${input.fileCount} فایل آپلود شد` : 'بدون فایل';

  const detectedScope = [
    'بازبینی فضاهای اصلی و وضعیت فعلی',
    /کابینت|آشپزخانه|اتاق|دکور|رنگ/i.test(descriptionText) ? 'بررسی جزئیات داخلی و کابینت‌سازی' : 'بررسی نیازهای عملکردی و زیبایی‌ شناختی',
    /حمام|دوش|سرویس|تأسیسات|لوله|آب/i.test(descriptionText) ? 'ارزیابی تأسیسات و سرویس‌بهداشتی' : 'بررسی ناحیه‌های کاری و نقاط حساس محیط',
    areaValue > 0 ? `برآورد متراژ تقریبی ${new Intl.NumberFormat('fa-IR').format(areaValue)} مترمربع` : 'تخمین اولیه بر اساس توضیحات متنی پروژه',
    fileLabel,
  ];

  const budgetBand =
    budgetValue >= 1500000000
      ? 'سطح لوکس / استاندارد بالا'
      : budgetValue >= 700000000
        ? 'سطح استاندارد'
        : budgetValue >= 300000000
          ? 'سطح اقتصادی'
          : 'نیاز به بازبینی بودجه';

  const estimatedRange =
    areaValue > 0
      ? `${formatCurrency(Math.round(areaValue * 1800000))} تا ${formatCurrency(Math.round(areaValue * 3200000))}`
      : budgetValue > 0
        ? `${formatCurrency(Math.round(budgetValue * 0.7))} تا ${formatCurrency(Math.round(budgetValue * 1.2))}`
        : 'در انتظار ورود بودجه و متراژ';

  const wbs: WorkPackage[] = [
    { order: 1, phase: 'تخریب و آماده‌سازی', tasks: ['بازدید و ثبت وضعیت موجود', 'محافظت از بخش‌های قابل نگهداری', 'جمع‌آوری و تخلیه مصالح فرسوده'] },
    { order: 2, phase: 'تأسیسات', tasks: ['بررسی مسیرهای آب و برق', 'رفع ایرادهای ضروری و آماده‌سازی زیرکار'] },
    { order: 3, phase: 'ساخت و اصلاح فضا', tasks: ['اصلاح دیوارها و سطوح', 'تراز و آماده‌سازی کف و سقف'] },
    { order: 4, phase: 'پوشش‌ها', tasks: ['اجرای کف و دیوار', 'آماده‌سازی و اجرای سقف'] },
    { order: 5, phase: 'کابینت و درب', tasks: ['اندازه‌گیری نهایی', 'انتخاب و نصب کابینت، درب و یراق‌آلات'] },
    { order: 6, phase: 'رنگ و دکور', tasks: ['رنگ‌آمیزی نهایی', 'نصب تجهیزات و کنترل کیفیت تحویل'] },
  ];

  const materials: MaterialSuggestion[] = [
    {
      category: 'کف و دیوار',
      suggestion: budgetValue >= 1500000000 ? 'سرامیک پرسلان با ابعاد بزرگ' : 'سرامیک مات با دوام متوسط تا بالا',
      reason: 'تعادل بین دوام، نظافت‌پذیری و سطح بودجه پروژه',
    },
    {
      category: 'رنگ',
      suggestion: 'رنگ قابل شست‌وشو با پایه آب',
      reason: 'مناسب برای نگهداری ساده و کاهش بوی اجرای پروژه',
    },
    {
      category: 'کابینت و چوب',
      suggestion: budgetValue >= 700000000 ? 'MDF با روکش مقاوم و یراق‌آلات آرام‌بند' : 'MDF اقتصادی با یراق‌آلات قابل تعویض',
      reason: 'قابل تنظیم با بودجه و قابل ارتقا در مراحل بعدی',
    },
  ];

  const estimateBase = areaValue > 0 ? areaValue * 1800000 : budgetValue > 0 ? budgetValue * 0.7 : 0;
  const estimateCeiling = areaValue > 0 ? areaValue * 3200000 : budgetValue > 0 ? budgetValue * 1.2 : 0;
  const phaseDurations = ['۳ تا ۵ روز', '۴ تا ۷ روز', '۳ تا ۶ روز', '۵ تا ۹ روز', '۷ تا ۱۴ روز', '۳ تا ۶ روز'];
  const phaseWeights = [0.1, 0.16, 0.14, 0.2, 0.25, 0.15];
  const estimate: ProjectEstimate = {
    totalCost: estimatedRange,
    duration: areaValue > 0 ? `${Math.max(3, Math.ceil(areaValue / 18))} تا ${Math.max(7, Math.ceil(areaValue / 9))} هفته` : 'برای تخمین زمان، متراژ وارد کنید',
    uncertainty: 'حدود ۲۰٪ تا ۳۰٪؛ وابسته به وضعیت پنهان تأسیسات، انتخاب متریال و تغییرات حین اجرا',
    pricingSource: activePricingSource.label,
    pricingStatus: 'provisional',
    lineItems: wbs.map((workPackage, index) => ({
      phase: workPackage.phase,
      cost: estimateBase > 0 ? `${formatCurrency(Math.round(estimateBase * phaseWeights[index]))} تا ${formatCurrency(Math.round(estimateCeiling * phaseWeights[index]))}` : 'پس از ورود بودجه یا متراژ',
      duration: phaseDurations[index],
    })),
  };

  const scenarioFactors = [
    { name: 'اقتصادی', description: 'تمرکز بر کنترل هزینه و حفظ عملکرد اصلی', factor: 0.75, materialLevel: 'متریال اقتصادی و قابل ارتقا' },
    { name: 'استاندارد', description: 'تعادل بین دوام، ظاهر و هزینه', factor: 1, materialLevel: 'متریال استاندارد بازار تهران' },
    { name: 'باکیفیت', description: 'اولویت با دوام، جزئیات اجرا و کیفیت نهایی', factor: 1.35, materialLevel: 'متریال باکیفیت و یراق‌آلات بهتر' },
    { name: 'مناسب اجاره', description: 'تحویل سریع، مقاوم و کم‌هزینه برای اجاره‌دادن', factor: 0.85, materialLevel: 'متریال مقاوم با نگهداری ساده' },
  ];
  const scenarios: ProjectScenario[] = scenarioFactors.map((scenario) => ({
    name: scenario.name,
    description: scenario.description,
    cost: estimateBase > 0
      ? `${formatCurrency(Math.round(estimateBase * scenario.factor))} تا ${formatCurrency(Math.round(estimateCeiling * scenario.factor))}`
      : 'پس از ورود بودجه یا متراژ',
    duration: areaValue > 0 ? `${Math.max(2, Math.ceil((areaValue / 18) * (scenario.name === 'باکیفیت' ? 1.15 : 1)))} تا ${Math.max(5, Math.ceil((areaValue / 9) * (scenario.name === 'اقتصادی' ? 0.9 : 1)))} هفته` : 'پس از ورود متراژ',
    materialLevel: scenario.materialLevel,
  }));

  return {
    title,
    source: 'fallback',
    budgetBand,
    estimatedRange,
    estimate,
    scenarios,
    scope: detectedScope.filter(Boolean),
    wbs,
    materials,
    nextSteps: [
      'تکمیل و استانداردسازی scope پروژه',
      'تولید WBS مرحله‌ای بر اساس فضاهای شناسایی‌شده',
      'پیشنهاد متریال و سناریوهای هزینه براساس بودجه',
      'قابل‌اشتراک‌سازی برای مجری/کارفرما در قالب brief',
    ],
  };
}
