import { NextResponse } from 'next/server';

import { generateProjectSummary, type ProjectIntakeInput } from '@/lib/project-intake';

export const runtime = 'nodejs';

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

  const summary = generateProjectSummary(body);
  return NextResponse.json(summary);
}