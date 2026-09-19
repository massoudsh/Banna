const test = require('node:test');
const assert = require('node:assert/strict');

const { generateProjectSummary } = require('./project-intake.ts');

test('generates a budget band and scope summary for a renovation project', () => {
  const summary = generateProjectSummary({
    projectName: 'آپارتمان ۳ خواب تهران',
    description: 'بازسازی آشپزخانه و حمام، نیاز به رنگ دیوار و کابینت جدید',
    budget: '950000000',
    surfaceArea: '120',
    fileCount: 2,
    fileNames: ['front.jpg', 'living-room.mp4'],
  });

  assert.equal(summary.title, 'آپارتمان ۳ خواب تهران');
  assert.equal(summary.source, 'fallback');
  assert.match(summary.estimate.duration, /هفته/);
  assert.equal(summary.estimate.lineItems.length, 6);
  assert.ok(summary.estimate.uncertainty.includes('۲۰٪'));
  assert.equal(summary.estimate.pricingStatus, 'provisional');
  assert.equal(summary.scenarios.length, 4);
  assert.equal(summary.scenarios[0].name, 'اقتصادی');
  assert.equal(summary.scenarios.at(-1).name, 'مناسب اجاره');
  assert.equal(summary.budgetBand, 'سطح استاندارد');
  assert.ok(summary.scope.some((item) => item.includes('آشپزخانه')) || summary.scope.some((item) => item.includes('تأسیسات')));
  assert.equal(summary.wbs.length, 6);
  assert.equal(summary.wbs[0].phase, 'تخریب و آماده‌سازی');
  assert.equal(summary.wbs.at(-1).phase, 'رنگ و دکور');
  assert.equal(summary.materials.length, 3);
  assert.ok(summary.materials.some((item) => item.category === 'کابینت و چوب'));
  assert.ok(summary.nextSteps.length >= 4);
});
