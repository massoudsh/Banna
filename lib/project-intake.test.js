const test = require('node:test');
const assert = require('node:assert/strict');

const {
  ENGINE_UNAVAILABLE_MESSAGE,
  buildSummary,
  generateProjectSummary,
} = require('./project-intake.ts');

/** نمونهٔ خروجی واقعی موتور پایتون (scripts/pipeline_json.py). */
const ENGINE_RESULT = {
  selected: 'standard',
  total_area_m2: 46.4,
  style: 'modern',
  budget_toman: null,
  spaces: [
    {
      space: 'kitchen',
      label_fa: 'آشپزخانه',
      area_m2: 33.14,
      condition: 'فرسوده',
      requested_works: ['تخریب'],
    },
    {
      space: 'bathroom',
      label_fa: 'حمام و سرویس',
      area_m2: 13.26,
      condition: 'متوسط',
      requested_works: ['تخریب'],
    },
  ],
  scenarios: [
    {
      kind: 'economy',
      label_fa: 'اقتصادی',
      tier: 'economy',
      description: 'کمترین هزینهٔ قابل‌قبول',
      cost_min_toman: 263057436,
      cost_max_toman: 452647647,
      duration_days_min: 14,
      duration_days_max: 19,
    },
    {
      kind: 'standard',
      label_fa: 'استاندارد',
      tier: 'standard',
      description: 'تعادل هزینه و کیفیت',
      cost_min_toman: 420584130,
      cost_max_toman: 744095310,
      duration_days_min: 15,
      duration_days_max: 21,
    },
    {
      kind: 'premium',
      label_fa: 'باکیفیت',
      tier: 'premium',
      description: 'بالاترین کیفیت اجرا',
      cost_min_toman: 898435584,
      cost_max_toman: 1707396490,
      duration_days_min: 19,
      duration_days_max: 26,
    },
    {
      kind: 'rental',
      label_fa: 'مناسب اجاره',
      tier: 'economy',
      description: 'بهینه برای اجارهٔ سریع',
      cost_min_toman: 145289808,
      cost_max_toman: 251800607,
      duration_days_min: 11,
      duration_days_max: 15,
    },
  ],
  wbs_items: [
    {
      code: 'KIT-DEM',
      title: 'تخریب کابینت',
      phase: 'demolition',
      phase_label_fa: 'تخریب',
      space: 'kitchen',
      space_label_fa: 'آشپزخانه',
      quantity: 1,
      unit: 'مورد',
      material: null,
    },
    {
      code: 'KIT-COV-F',
      title: 'کفپوش آشپزخانه',
      phase: 'covering',
      phase_label_fa: 'پوشش کف و دیوار',
      space: 'kitchen',
      space_label_fa: 'آشپزخانه',
      quantity: 33.14,
      unit: 'مترمربع',
      material: 'سرامیک پرسلان',
    },
    {
      code: 'BAT-COV-T',
      title: 'کاشی‌کاری سرویس',
      phase: 'covering',
      phase_label_fa: 'پوشش کف و دیوار',
      space: 'bathroom',
      space_label_fa: 'حمام و سرویس',
      quantity: 13.26,
      unit: 'مترمربع',
      material: 'کاشی ایرانی درجه ۱',
    },
  ],
  assumptions: ['وضعیت فعلی فضا از متن قابل تشخیص نبود؛ «متوسط» فرض شد.'],
  missing_price_codes: [],
};

const INPUT = {
  projectName: 'آپارتمان ۳ خواب تهران',
  description: 'بازسازی آشپزخانه و حمام',
  budget: '950000000',
  surfaceArea: '80',
  fileCount: 2,
  fileNames: ['front.jpg', 'living-room.mp4'],
};

test('maps engine output into the display model', () => {
  const summary = buildSummary(INPUT, ENGINE_RESULT);

  assert.equal(summary.title, 'آپارتمان ۳ خواب تهران');
  assert.equal(summary.source, 'engine');
  assert.equal(summary.budgetBand, 'سطح استاندارد');
  assert.equal(summary.scenarios.length, 4);
  assert.equal(summary.scenarios[0].name, 'اقتصادی');
  assert.equal(summary.scenarios.at(-1).name, 'مناسب اجاره');
});

test('selected scenario drives the headline numbers', () => {
  const summary = buildSummary(INPUT, ENGINE_RESULT);
  // سناریوی انتخابی `standard` است، نه اولی یا آخری.
  assert.match(summary.estimate.totalCost, /۴۲۰٫۵۸۴٫۱۳۰|420,584,130/);
  assert.ok(summary.estimate.duration.includes('روز'));
  assert.match(summary.estimatedRange, /تومان/);
});

test('wbs items are grouped by phase in execution order', () => {
  const summary = buildSummary(INPUT, ENGINE_RESULT);
  assert.equal(summary.wbs[0].phase, 'تخریب');
  assert.equal(summary.wbs.at(-1).phase, 'پوشش کف و دیوار');
  assert.ok(summary.wbs[0].tasks[0].includes('کابینت'));
});

test('line items cover every phase and sum to the selected range', () => {
  const summary = buildSummary(INPUT, ENGINE_RESULT);
  assert.equal(summary.estimate.lineItems.length, summary.wbs.length);
  const counted = summary.estimate.lineItems.reduce((sum, item) => sum + item.itemCount, 0);
  assert.equal(counted, ENGINE_RESULT.wbs_items.length);
});

test('engine assumptions reach the user as warnings', () => {
  const summary = buildSummary(INPUT, ENGINE_RESULT);
  assert.ok(summary.warnings.includes(ENGINE_RESULT.assumptions[0]));
  assert.equal(summary.missingPriceCodes.length, 0);
  assert.equal(summary.estimate.pricingStatus, 'calibrated');
});

test('unpriced items are surfaced, never silently dropped', () => {
  const withGap = { ...ENGINE_RESULT, missing_price_codes: ['KIT-JOI-C'] };
  const summary = buildSummary(INPUT, withGap);

  assert.equal(summary.estimate.pricingStatus, 'provisional');
  assert.deepEqual(summary.missingPriceCodes, ['KIT-JOI-C']);
  assert.ok(summary.warnings.some((warning) => warning.includes('KIT-JOI-C')));
  assert.match(summary.estimate.uncertainty, /ناقص/);
});

test('materials come from priced wbs items, one card per space', () => {
  const summary = buildSummary(INPUT, ENGINE_RESULT);
  assert.equal(summary.materials.length, 2);
  assert.ok(summary.materials.some((material) => material.suggestion === 'سرامیک پرسلان'));
});

test('scope lines report area and condition per space', () => {
  const summary = buildSummary(INPUT, ENGINE_RESULT);
  assert.equal(summary.scope.length, 2);
  assert.ok(summary.scope[0].includes('آشپزخانه'));
  assert.ok(summary.scope[0].includes('فرسوده'));
});

test('missing budget does not fabricate a band', () => {
  const summary = buildSummary({ ...INPUT, budget: '' }, ENGINE_RESULT);
  assert.equal(summary.budgetBand, 'بودجه‌ای اعلام نشده');
});

test('summary carries no hardcoded price constants', () => {
  // رگرسیون: لایهٔ وب نباید فرمول قیمت مستقل داشته باشد.
  const source = require('node:fs').readFileSync(
    require('node:path').join(__dirname, 'project-intake.ts'),
    'utf8',
  );
  assert.ok(!/1800000|3200000/.test(source), 'ثابت قیمتی قدیمی در لایهٔ وب باقی مانده');
});

test('engine failure is reported instead of guessed numbers', async () => {
  await assert.rejects(
    () => generateProjectSummary(INPUT),
    (error) => {
      assert.equal(error.code, 'not_configured');
      assert.equal(error.message, ENGINE_UNAVAILABLE_MESSAGE);
      return true;
    },
  );
});
