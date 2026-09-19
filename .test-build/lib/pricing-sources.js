"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activePricingSource = exports.pricingSources = void 0;
exports.pricingSources = [
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
exports.activePricingSource = exports.pricingSources[0];
