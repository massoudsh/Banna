import { NextResponse } from 'next/server';

import {
  ENGINE_UNAVAILABLE_MESSAGE,
  PipelineError,
  generateProjectSummary,
  type ProjectIntakeInput,
} from '@/lib/project-intake';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function isProjectIntakeInput(value: unknown): value is ProjectIntakeInput {
  if (!value || typeof value !== 'object') return false;

  const input = value as Partial<ProjectIntakeInput>;
  return (
    typeof input.projectName === 'string' &&
    typeof input.description === 'string' &&
    typeof input.budget === 'string' &&
    typeof input.surfaceArea === 'string' &&
    typeof input.fileCount === 'number' &&
    Array.isArray(input.fileNames) &&
    input.fileNames.every((fileName) => typeof fileName === 'string')
  );
}

export async function POST(request: Request) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'درخواست نامعتبر است.' }, { status: 400 });
  }

  if (!isProjectIntakeInput(body) || !body.projectName.trim()) {
    return NextResponse.json({ error: 'نام پروژه الزامی است.' }, { status: 400 });
  }

  try {
    const summary = await generateProjectSummary(body);
    return NextResponse.json(summary);
  } catch (error) {
    if (error instanceof PipelineError) {
      // خطای دامنه (متراژ/توضیح نامعتبر) پیام موتور را عیناً برمی‌گرداند؛
      // نبود موتور ۵۰۳ است چون رفع آن کار اپراتور است، نه اصلاح ورودی.
      return NextResponse.json(
        { error: error.code === 'not_configured' ? ENGINE_UNAVAILABLE_MESSAGE : error.message },
        { status: error.code === 'not_configured' ? 503 : 400 },
      );
    }
    return NextResponse.json(
      { error: 'پردازش پروژه انجام نشد. لطفاً دوباره تلاش کنید.' },
      { status: 500 },
    );
  }
}