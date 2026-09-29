from decimal import Decimal


ZERO=Decimal("0")
VARIABLE_TYPES={"per_liter","per_drum","percent_profit","commission"}


def normalize_salary_type(profile):
    return ((profile.salary_type if profile else "fixed") or "fixed").strip()


def salary_value(profile):
    return Decimal(str(profile.salary_value or 0)) if profile else ZERO


def calculate_commission_amount(salary_type,value,liters=0,drums=0,gross_profit=0):
    salary_type=salary_type or "fixed"
    value=Decimal(str(value or 0))
    liters=Decimal(str(liters or 0))
    drums=Decimal(str(drums or 0))
    gross_profit=Decimal(str(gross_profit or 0))

    if salary_type=="per_liter":
        return liters*value
    if salary_type=="per_drum":
        return drums*value
    if salary_type in {"percent_profit","commission"}:
        return max(gross_profit,ZERO)*value/Decimal("100")
    return ZERO


def apply_employee_compensation_snapshot(dispense,profile):
    salary_type=normalize_salary_type(profile)
    value=salary_value(profile)
    dispense.employee_compensation_type=salary_type
    dispense.employee_compensation_value=value

    if salary_type in VARIABLE_TYPES:
        dispense.employee_commission_amount=calculate_commission_amount(
            salary_type,
            value,
            liters=dispense.liters,
            drums=dispense.drums,
            gross_profit=dispense.gross_profit,
        )
    else:
        dispense.employee_commission_amount=ZERO

    return dispense


def compensation_label(salary_type,value,currency="ريال"):
    value=Decimal(str(value or 0))
    if salary_type=="per_liter":
        return f"{value} {currency}/لتر"
    if salary_type=="per_drum":
        return f"{value} {currency}/دبة"
    if salary_type in {"percent_profit","commission"}:
        return f"{value}% من الربح"
    return f"راتب ثابت {value} {currency}"
