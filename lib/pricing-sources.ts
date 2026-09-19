export type PricingSource = {
  id: string;
  label: string;
  kind: 'government-labor' | 'market-material';
  geography: string;
  status: 'configured' | 'needs-import';
  sourceUrl: string;
  notes: string;
};

export const pricingSources: PricingSource[] = [
  {
    id: 'iran-government-interregional-labor',
    label: 'فهرست‌بهای پایه ابنیه و ضرایب منطقه‌ای نظام فنی و اجرایی دولت',
    kind: 'government-labor',
    geography: 'تهران / منطقه مربوطه',
    status: 'needs-import',
    sourceUrl: 'https://www.mporg.ir',
    notes: 'منبع مبنای دستمزد و عملیات اجرایی است؛ باید نسخه سال جاری و ضریب منطقه‌ای تهران به‌صورت رسمی وارد شود.',
  },
  {
    id: 'tehran-market-materials',
    label: 'قیمت بازار متریال بازسازی تهران',
    kind: 'market-material',
    geography: 'تهران',
    status: 'needs-import',
    sourceUrl: 'https://www.amar.org.ir',
    notes: 'قیمت فروش متریال باید از چند فروشنده/استعلام روزانه جمع‌آوری و با تاریخ اعتبار ذخیره شود؛ آمار دولتی به‌تنهایی quote فروشنده نیست.',
  },
];

export const activePricingSource = pricingSources[0];