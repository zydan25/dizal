from decimal import Decimal
from types import SimpleNamespace

from app.services.reports import calculate_employee_compensation
from app.services.compensation import apply_employee_compensation_snapshot


def profile(salary_type, salary_value):
    return SimpleNamespace(salary_type=salary_type, salary_value=Decimal(str(salary_value)))


def test_per_drum_commission_uses_all_drums():
    result=calculate_employee_compensation(
        profile("per_drum",500),
        sales=Decimal("1300000"),
        cogs=Decimal("900000"),
        liters=Decimal("2000"),
        drums=Decimal("100"),
        currency="ريال",
    )
    assert result["earned"] == Decimal("50000")
    assert result["gross_profit"] == Decimal("400000")


def test_per_liter_commission():
    result=calculate_employee_compensation(
        profile("per_liter",25),
        sales=Decimal("1300000"),
        cogs=Decimal("900000"),
        liters=Decimal("2000"),
        drums=Decimal("100"),
        currency="ريال",
    )
    assert result["earned"] == Decimal("50000")
    assert result["label"] == "25 ريال/لتر"


def test_percent_profit_commission_is_based_on_positive_gross_profit():
    result=calculate_employee_compensation(
        profile("percent_profit",10),
        sales=Decimal("1300000"),
        cogs=Decimal("900000"),
        liters=Decimal("2000"),
        drums=Decimal("100"),
        currency="ريال",
    )
    assert result["earned"] == Decimal("40000")


def test_percent_profit_does_not_create_negative_commission():
    result=calculate_employee_compensation(
        profile("percent_profit",10),
        sales=Decimal("900000"),
        cogs=Decimal("1000000"),
        liters=Decimal("2000"),
        drums=Decimal("100"),
        currency="ريال",
    )
    assert result["earned"] == Decimal("0")


def test_fixed_salary_returns_configured_period_amount():
    result=calculate_employee_compensation(
        profile("fixed",75000),
        sales=Decimal("1300000"),
        cogs=Decimal("900000"),
        liters=Decimal("2000"),
        drums=Decimal("100"),
        currency="ريال",
    )
    assert result["earned"] == Decimal("75000")
    assert result["label"] == "راتب ثابت 75000 ريال"


def test_per_drum_snapshot_freezes_value_on_sale():
    sale=SimpleNamespace(
        liters=Decimal("2000"),
        drums=Decimal("100"),
        gross_profit=Decimal("400000"),
        employee_compensation_type=None,
        employee_compensation_value=None,
        employee_commission_amount=Decimal("0"),
    )
    apply_employee_compensation_snapshot(sale,profile("per_drum",500))
    assert sale.employee_compensation_type=="per_drum"
    assert sale.employee_compensation_value==Decimal("500")
    assert sale.employee_commission_amount==Decimal("50000")


def test_percent_profit_snapshot_uses_actual_sale_profit():
    sale=SimpleNamespace(
        liters=Decimal("2000"),
        drums=Decimal("100"),
        gross_profit=Decimal("400000"),
        employee_compensation_type=None,
        employee_compensation_value=None,
        employee_commission_amount=Decimal("0"),
    )
    apply_employee_compensation_snapshot(sale,profile("percent_profit",10))
    assert sale.employee_commission_amount==Decimal("40000")


def test_snapshot_does_not_change_when_profile_changes():
    sale=SimpleNamespace(
        liters=Decimal("2000"),
        drums=Decimal("100"),
        gross_profit=Decimal("400000"),
        employee_compensation_type=None,
        employee_compensation_value=None,
        employee_commission_amount=Decimal("0"),
    )
    apply_employee_compensation_snapshot(sale,profile("per_drum",500))
    before=sale.employee_commission_amount
    changed_profile=profile("per_drum",600)
    assert changed_profile.salary_value==Decimal("600")
    assert sale.employee_commission_amount==before==Decimal("50000")
