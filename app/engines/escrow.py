"""Escrow milestone state transitions backed by WBS completion evidence."""

from __future__ import annotations

from app.models.domain import EscrowMilestone, ProjectExecutionChecklist


class EscrowError(ValueError):
    """تغییر وضعیت امانی با وضعیت مایلستون سازگار نیست."""


def release(milestone: EscrowMilestone, checklist: ProjectExecutionChecklist) -> EscrowMilestone:
    item = next((entry for entry in checklist.items if entry.wbs_code == milestone.wbs_code), None)
    if milestone.status != "pending":
        raise EscrowError("فقط مبلغ امانی در انتظار آزادسازی قابل آزادسازی است.")
    if item is None or item.status != "done" or not item.evidence_filenames:
        raise EscrowError("برای آزادسازی، مایلستون باید تکمیل و دارای تأیید تصویری باشد.")
    return milestone.model_copy(update={"status": "released"})


def block(milestone: EscrowMilestone, reason: str) -> EscrowMilestone:
    if milestone.status != "pending":
        raise EscrowError("فقط مبلغ امانی در انتظار را می‌توان مسدود کرد.")
    if not reason.strip():
        raise EscrowError("علت اختلاف برای مسدودسازی لازم است.")
    return milestone.model_copy(update={"status": "blocked", "dispute_reason": reason.strip()})


def refund(milestone: EscrowMilestone) -> EscrowMilestone:
    if milestone.status != "blocked":
        raise EscrowError("بازگشت وجه فقط برای مبلغ مسدودشده ممکن است.")
    return milestone.model_copy(update={"status": "refunded"})
