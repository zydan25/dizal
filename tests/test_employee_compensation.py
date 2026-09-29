from decimal import Decimal
from types import SimpleNamespace

from app.services.reports import calculate_employee_compensation


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
