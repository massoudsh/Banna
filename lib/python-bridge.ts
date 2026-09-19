import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

/**
 * پل به موتورهای پایتون.
 *
 * تنها منبع حقیقت تخمین، `app/pipeline.py` است؛ لایهٔ Next.js هیچ فرمول قیمتی
 * مستقل ندارد. این فایل خروجی ساختاریافتهٔ pipeline را به‌صورت JSON می‌گیرد.
 *
 * انتخاب رویکرد subprocess به‌جای HTTP عمدی است: سرویس FastAPI در MVP پروژه‌ها
 * را در حافظهٔ خود نگه می‌دارد و ممکن است در همان فرایند بالا نیامده باشد؛
 * فراخوانی مستقیم CLI همان موتور را بدون وابستگی به وضعیت سرویس اجرا می‌کند.
 */

export type PipelineWbsItem = {
  code: string;
  title: string;
  phase: string;
  phase_label_fa: string;
  space: string;
  space_label_fa: string;
  quantity: number;
  unit: string;
  material: string | null;
};

export type PipelineScenario = {
  kind: string;
  label_fa: string;
  tier: string;
  description: string;
  cost_min_toman: number;
  cost_max_toman: number;
  duration_days_min: number;
  duration_days_max: number;
};

export type PipelineResult = {
  selected: string;
  total_area_m2: number;
  style: string;
  budget_toman: number | null;
  spaces: {
    space: string;
    label_fa: string;
    area_m2: number;
    condition: string;
    requested_works: string[];
  }[];
  scenarios: PipelineScenario[];
  wbs_items: PipelineWbsItem[];
  assumptions: string[];
  missing_price_codes: string[];
};

export type BridgeInput = {
  description: string;
  totalAreaM2?: number | null;
  title?: string;
};

export class PipelineError extends Error {
  constructor(
    message: string,
    readonly code: 'not_configured' | 'failed',
  ) {
    super(message);
    this.name = 'PipelineError';
  }
}

function projectRoot(): string {
  return process.env.BANNA_PROJECT_ROOT ?? process.cwd();
}

export function pythonExecutable(): string {
  return process.env.BANNA_PYTHON ?? 'python3';
}

/** مسیر اسکریپت پل — در ریشهٔ پروژه، کنار موتورهای پایتون. */
export function bridgeScript(): string {
  return path.join(projectRoot(), 'scripts', 'pipeline_json.py');
}

export function isBridgeConfigured(): boolean {
  return existsSync(bridgeScript());
}

/**
 * اجرای pipeline پایتون و برگرداندن خروجی ساختاریافته.
 *
 * خطاهای دامنه (`WBSError`، `ScopeError`، `MediaValidationError`) با کد ۲ بر
 * می‌گردند و پیام فارسی‌شان دست‌نخورده به UI می‌رسد؛ خطای محیطی (نبود
 * مفسر/اسکریپت) با `not_configured` مشخص می‌شود تا UI بتواند فرق بگذارد.
 */
export function runPipeline(input: BridgeInput): Promise<PipelineResult> {
  if (!isBridgeConfigured()) {
    return Promise.reject(
      new PipelineError('اسکریپت پل پایتون پیدا نشد.', 'not_configured'),
    );
  }

  const args = [bridgeScript(), '--description', input.description];
  if (input.totalAreaM2 != null && input.totalAreaM2 > 0) {
    args.push('--area', String(input.totalAreaM2));
  }

  return new Promise<PipelineResult>((resolve, reject) => {
    const child = spawn(pythonExecutable(), args, {
      cwd: projectRoot(),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk;
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });

    child.on('error', () => {
      reject(
        new PipelineError('اجرای موتور پایتون ممکن نشد.', 'not_configured'),
      );
    });

    child.on('close', (code) => {
      if (code === 0) {
        try {
          resolve(JSON.parse(stdout) as PipelineResult);
        } catch {
          reject(new PipelineError('خروجی موتور قابل‌خواندن نبود.', 'failed'));
        }
        return;
      }

      const message = stdout.trim() || stderr.trim().split('\n').pop() || '';
      reject(
        new PipelineError(
          message || 'پردازش پروژه در موتور تخمین انجام نشد.',
          'failed',
        ),
      );
    });
  });
}
