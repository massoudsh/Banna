"""تست WBS engine (Issue #7)."""

import pytest

from app.engines.scope import analyze
from app.engines.wbs import WBSError, generate, load_reference
from app.models.domain import PHASE_ORDER, SpaceType, WorkPhase


def _scope(text="آشپزخانه بازسازی کامل", area=80):
    return analyze(text, total_area_m2=area)


class TestReferenceData:
    def test_reference_loads(self):
        ref = load_reference()
        assert "spaces" in ref and ref["spaces"]

    def test_all_four_mvp_spaces_covered(self):
        """دامنهٔ MVP چهار فضا دارد (Issue #4) — همه باید WBS داشته باشند."""
        ref = load_reference()
        for space in SpaceType:
            assert space.value in ref["spaces"], f"{space.value} در WBS مرجع نیست"

    def test_every_item_has_valid_phase(self):
        ref = load_reference()
        for space_key, spec in ref["spaces"].items():
            for item in spec["items"]:
                assert item["phase"] in {p.value for p in WorkPhase}, (
                    f"{space_key}/{item['code']} فاز نامعتبر دارد"
                )


class TestGenerate:
    def test_generates_items_for_kitchen(self):
        wbs = generate(_scope())
        assert wbs.items
        assert all(i.space == SpaceType.KITCHEN for i in wbs.items)

    def test_output_sorted_by_phase_order(self):
        wbs = generate(_scope("آشپزخانه و حمام بازسازی کامل", area=80))
        indexes = [PHASE_ORDER.index(i.phase) for i in wbs.items]
        assert indexes == sorted(indexes), "ترتیب فازها رعایت نشده"

    def test_multi_space_supported(self):
        wbs = generate(_scope("آشپزخانه و حمام و نشیمن و خواب بازسازی کامل", area=100))
        assert len({i.space for i in wbs.items}) == 4

    def test_demolition_comes_before_covering(self):
        wbs = generate(_scope())
        phases = [i.phase for i in wbs.items]
        assert phases.index(WorkPhase.DEMOLITION) < phases.index(WorkPhase.COVERING)

    def test_fixed_unit_items_have_quantity_one(self):
        wbs = generate(_scope())
        fixed = [i for i in wbs.items if i.unit == "مورد"]
        assert fixed
        assert all(i.quantity == 1.0 for i in fixed)

    def test_area_based_quantity_scales_with_area(self):
        small = generate(_scope(area=50))
        large = generate(_scope(area=100))
        small_item = next(i for i in small.items if i.code == "KIT-COV-F")
        large_item = next(i for i in large.items if i.code == "KIT-COV-F")
        assert large_item.quantity == pytest.approx(small_item.quantity * 2, rel=0.01)

    def test_only_requested_phases_included(self):
        wbs = generate(_scope("آشپزخانه فقط رنگ و کاشی", area=80))
        faces = {i.phase for i in wbs.items}
        assert WorkPhase.DEMOLITION not in faces
        assert WorkPhase.COVERING in faces

    def test_dependencies_form_chain_across_phases(self):
        wbs = generate(_scope())
        covering = next(i for i in wbs.items if i.phase == WorkPhase.COVERING)
        assert covering.depends_on, "آیتم پوشش باید به فاز قبل وابسته باشد"

    def test_codes_are_unique(self):
        wbs = generate(_scope("آشپزخانه و حمام بازسازی کامل", area=80))
        codes = [i.code for i in wbs.items]
        assert len(codes) == len(set(codes)), "کد آیتم تکراری است"

    def test_raises_on_empty_scope(self):
        from app.models.domain import ScopeSummary

        with pytest.raises(WBSError):
            generate(ScopeSummary(spaces=[]))

    def test_all_dependencies_reference_existing_items(self):
        """رگرسیون: وابستگی به کد ناموجود، مسیر بحرانی را می‌شکند."""
        wbs = generate(_scope("آشپزخانه و حمام بازسازی کامل", area=80))
        codes = {i.code for i in wbs.items}
        for item in wbs.items:
            for dep in item.depends_on:
                assert dep in codes, f"{item.code} به {dep} وابسته است که وجود ندارد"
