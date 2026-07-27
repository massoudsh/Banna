#!/usr/bin/env bash
# ایجاد دسته‌ای Issueهای docs/issues/ روی مخزن GitHub متصل.
# پیش‌نیاز: gh CLI نصب و `gh auth login` انجام‌شده، و ریموت GitHub به این مخزن متصل باشد
# (این دو کار فقط از تنظیمات پروژه در پنل ممکن است).
#
# استفاده: bash scripts/create_github_issues.sh

set -euo pipefail

ISSUES_DIR="$(dirname "$0")/../docs/issues"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI پیدا نشد. ابتدا GitHub را از تنظیمات پروژه وصل کنید." >&2
  exit 1
fi

for f in "$ISSUES_DIR"/[0-9]*.md; do
  title=$(sed -n 's/^title: *"\(.*\)"$/\1/p' "$f" | head -1)
  labels=$(sed -n 's/^labels: *\[\(.*\)\]$/\1/p' "$f" | tr -d '[:space:]' | tr ',' ',')
  body=$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$f")

  echo "→ ایجاد Issue: $title"
  if [ -n "$labels" ]; then
    gh issue create --title "$title" --body "$body" --label "$labels"
  else
    gh issue create --title "$title" --body "$body"
  fi
done

echo "تمام Issueها ایجاد شدند."
