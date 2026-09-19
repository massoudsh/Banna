"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PipelineError = exports.ENGINE_UNAVAILABLE_MESSAGE = void 0;
exports.generateProjectSummary = generateProjectSummary;
exports.buildSummary = buildSummary;
const python_bridge_ts_1 = require("./python-bridge.ts");
Object.defineProperty(exports, "PipelineError", { enumerable: true, get: function () { return python_bridge_ts_1.PipelineError; } });
exports.ENGINE_UNAVAILABLE_MESSAGE = 'موتور تخمین در دسترس نیست. تا زمان اتصال، عدد تخمینی نمایش داده نمی‌شود.';
function parseNumber(value) {
    const normalized = value.replace(/[^0-9]/g, '');
    return normalized ? Number(normalized) : 0;
}
function formatCurrency(value) {
    return new Intl.NumberFormat('fa-IR').format(Math.round(value)) + ' تومان';
}
function formatRange(min, max) {
    return `${formatCurrency(min)} تا ${formatCurrency(max)}`;
}
function formatDays(min, max) {
    const fa = (n) => new Intl.NumberFormat('fa-IR').format(n);
    return `${fa(min)} تا ${fa(max)} روز`;
}
function budgetBand(budgetValue) {
    if (budgetValue >= 1500000000)
        return 'سطح لوکس / استاندارد بالا';
    if (budgetValue >= 700000000)
        return 'سطح استاندارد';
    if (budgetValue >= 300000000)
        return 'سطح اقتصادی';
    return 'نیاز به بازبینی بودجه';
}
/** گروه‌بندی آیتم‌های WBS موتور بر اساس فاز، با حفظ ترتیب اجرا. */
function toWorkPackages(result) {
    const order = [];
    const byPhase = new Map();
    for (const item of result.wbs_items) {
        const phase = item.phase_label_fa;
        if (!byPhase.has(phase)) {
            byPhase.set(phase, []);
            order.push(phase);
        }
        const tasks = byPhase.get(phase);
        const label = `${item.title} — ${item.space_label_fa}`;
        if (!tasks.includes(label))
            tasks.push(label);
    }
    return order.map((phase, index) => ({
        order: index + 1,
        phase,
        tasks: byPhase.get(phase),
    }));
}
function toLineItems(result, selectedCost) {
    const order = [];
    const counts = new Map();
    for (const item of result.wbs_items) {
        const phase = item.phase_label_fa;
        if (!counts.has(phase))
            order.push(phase);
        counts.set(phase, (counts.get(phase) ?? 0) + 1);
    }
    // سهم هر فاز از بازهٔ سناریوی انتخابی، متناسب با تعداد آیتم‌های همان فاز.
    const total = result.wbs_items.length || 1;
    return order.map((phase) => {
        const count = counts.get(phase) ?? 0;
        const share = count / total;
        return {
            phase,
            cost: formatRange(selectedCost[0] * share, selectedCost[1] * share),
            duration: `${count} آیتم`,
            itemCount: count,
        };
    });
}
function toMaterialSuggestions(result) {
    const order = [];
    const byCategory = new Map();
    for (const item of result.wbs_items) {
        if (!item.material)
            continue;
        const category = item.space_label_fa;
        if (byCategory.has(category))
            continue;
        order.push(category);
        byCategory.set(category, {
            category,
            suggestion: item.material,
            reason: `بر اساس آیتم ${item.code} (${item.phase_label_fa})`,
        });
    }
    return order.map((category) => byCategory.get(category));
}
function toScenarioCards(result) {
    return result.scenarios.map((scenario) => ({
        name: scenario.label_fa,
        description: scenario.description,
        cost: formatRange(scenario.cost_min_toman, scenario.cost_max_toman),
        duration: formatDays(scenario.duration_days_min, scenario.duration_days_max),
        materialLevel: scenario.tier,
    }));
}
function buildSummary(input, result) {
    const title = input.projectName.trim() || 'پروژه جدید';
    const budgetValue = parseNumber(input.budget);
    const selected = result.scenarios.find((scenario) => scenario.kind === result.selected) ??
        result.scenarios[0];
    const warnings = [...result.assumptions];
    if (result.missing_price_codes.length) {
        warnings.push(`برای ${result.missing_price_codes.length} آیتم قیمت ثبت نشده بود؛ این آیتم‌ها در تخمین لحاظ نشده‌اند: ${result.missing_price_codes.join('، ')}`);
    }
    return {
        title,
        source: 'engine',
        budgetBand: budgetValue > 0 ? budgetBand(budgetValue) : 'بودجه‌ای اعلام نشده',
        estimatedRange: formatRange(selected.cost_min_toman, selected.cost_max_toman),
        estimate: {
            totalCost: formatRange(selected.cost_min_toman, selected.cost_max_toman),
            duration: formatDays(selected.duration_days_min, selected.duration_days_max),
            uncertainty: result.missing_price_codes.length > 0
                ? 'تخمین ناقص است: بخشی از آیتم‌های WBS قیمت مصوب ندارند.'
                : 'بازه بر پایهٔ دیتاست قیمت تهران و دامنهٔ تغییرات متریال محاسبه شده است.',
            pricingSource: 'دیتاست قیمت متریال و دستمزد تهران (data/price_dataset.json)',
            pricingStatus: result.missing_price_codes.length ? 'provisional' : 'calibrated',
            lineItems: toLineItems(result, [selected.cost_min_toman, selected.cost_max_toman]),
        },
        scenarios: toScenarioCards(result),
        scope: result.spaces.map((space) => `${space.label_fa}: ${new Intl.NumberFormat('fa-IR').format(space.area_m2)} مترمربع (وضعیت ${space.condition})`),
        wbs: toWorkPackages(result),
        materials: toMaterialSuggestions(result),
        nextSteps: [
            'بررسی سند Brief و اصلاح آیتم‌های ناخواسته',
            'ارسال Brief برای مجریان و دریافت quote',
            'مقایسهٔ quoteها با بازهٔ تخمینی همین سند',
        ],
        warnings,
        missingPriceCodes: result.missing_price_codes,
    };
}
/**
 * اجرای موتور و ساخت خلاصهٔ پروژه.
 *
 * اگر موتور در دسترس نباشد `PipelineError` پرتاب می‌شود؛ فراخوان باید پیام را
 * به کاربر نشان دهد و **نباید** مقدار جایگزین حدسی بسازد.
 */
async function generateProjectSummary(input) {
    if (!(0, python_bridge_ts_1.isBridgeConfigured)()) {
        throw new python_bridge_ts_1.PipelineError(exports.ENGINE_UNAVAILABLE_MESSAGE, 'not_configured');
    }
    const area = parseNumber(input.surfaceArea);
    const result = await (0, python_bridge_ts_1.runPipeline)({
        description: input.description,
        totalAreaM2: area > 0 ? area : null,
    });
    return buildSummary(input, result);
}
