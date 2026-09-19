"""رتبه‌بندی شفاف مجریان (Issue #14)."""

from __future__ import annotations

from app.models.domain import ContractorProfile, ContractorRanking, ContractorReview


def rank(
    profiles: list[ContractorProfile], reviews: list[ContractorReview]
) -> list[ContractorRanking]:
    reviews_by_id: dict[str, list[ContractorReview]] = {p.contractor_id: [] for p in profiles}
    for review in reviews:
        if review.contractor_id in reviews_by_id:
            reviews_by_id[review.contractor_id].append(review)

    rankings = []
    for profile in profiles:
        contractor_reviews = reviews_by_id[profile.contractor_id]
        average = sum(r.rating for r in contractor_reviews) / len(contractor_reviews) if contractor_reviews else 0
        punctuality = sum(r.on_time for r in contractor_reviews) / len(contractor_reviews) if contractor_reviews else 0
        score = round(average / 5 * 70 + punctuality * 20 + min(profile.completed_projects, 10) + (10 if profile.verified else 0), 2)
        explanation = [f"میانگین رضایت: {average:.1f} از ۵" if contractor_reviews else "هنوز بازخوردی ثبت نشده است"]
        explanation.append(f"خوش‌قولی: {punctuality:.0%}" if contractor_reviews else "خوش‌قولی: داده‌ای ثبت نشده است")
        if profile.verified:
            explanation.append("احراز اولیه شده است")
        rankings.append(ContractorRanking(
            contractor_id=profile.contractor_id,
            score=score,
            review_count=len(contractor_reviews),
            verified=profile.verified,
            explanation=explanation,
        ))
    return sorted(rankings, key=lambda item: (-item.score, item.contractor_id))
