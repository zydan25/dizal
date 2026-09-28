from flask import render_template
from flask_login import current_user
from sqlalchemy import desc
from ...decorators import permission_required
from ...models import Cashbox,CashboxTransaction
from ...permissions import user_has_permission
from ...services.cashbox import balance
from . import cashbox_bp

@cashbox_bp.get("/")
@permission_required("cashbox.view")
def index():
    if user_has_permission(current_user,"cashbox.view_all"):
        boxes=Cashbox.query.filter_by(is_active=True).all()
    else:
        boxes=Cashbox.query.filter_by(owner_user_id=current_user.id,is_active=True).all()
    rows=[{"box":box,"balance":balance(box.id)} for box in boxes]
    return render_template("cashbox/index.html",rows=rows)

@cashbox_bp.get("/<int:cashbox_id>")
@permission_required("cashbox.view")
def detail(cashbox_id):
    box=Cashbox.query.get_or_404(cashbox_id)
    if not user_has_permission(current_user,"cashbox.view_all") and box.owner_user_id!=current_user.id:
        from flask import abort
        abort(403)
    transactions=CashboxTransaction.query.filter_by(cashbox_id=box.id).order_by(desc(CashboxTransaction.created_at)).limit(100).all()
    return render_template("cashbox/detail.html",box=box,balance=balance(box.id),transactions=transactions)
