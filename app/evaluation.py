"""Regression evaluation for structured Persian scope extraction."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.engines.scope import analyze


class EvaluationCase(BaseModel):
    case_id: str
    text: str
    expected_spaces: list[str] = Field(default_factory=list)
    expected_works: list[str] = Field(default_factory=list)
    expected_style: str = "modern"
    expected_condition: str = "fair"


class EvaluationResult(BaseModel):
    case_id: str
    passed: bool
    matched: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)


def load_cases(path: Path) -> list[EvaluationCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationCase.model_validate(item) for item in data["cases"]]


def evaluate_case(case: EvaluationCase) -> EvaluationResult:
    scope = analyze(case.text)
    actual_spaces = [space.space.value for space in scope.spaces]
    actual_works = [work.value for work in scope.spaces[0].requested_works]
    assertions = {
        "spaces": actual_spaces == case.expected_spaces,
        "works": actual_works == case.expected_works,
        "style": scope.style == case.expected_style,
        "condition": scope.spaces[0].condition.value == case.expected_condition,
    }
    return EvaluationResult(
        case_id=case.case_id,
        passed=all(assertions.values()),
        matched=[name for name, result in assertions.items() if result],
        failed=[name for name, result in assertions.items() if not result],
    )


def evaluate(path: Path) -> list[EvaluationResult]:
    return [evaluate_case(case) for case in load_cases(path)]
