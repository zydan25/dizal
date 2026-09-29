from ..extensions import db
from ..models import Asset,FuelTank
from .cashbox import post_transaction
from .documents import create_document

def create_asset(name,category,cost,acquisition_date,payer_cashbox_id,created_by_id,custodian_user_id=None,location=None,notes=None,create_tank=False,tank_capacity_liters=None):
    if float(cost)<=0: raise ValueError("قيمة الأصل يجب أن تكون أكبر من صفر.")
    code=f"AST-{Asset.query.count()+1:06d}"
    document=create_document("AST","سند شراء أصل",created_by_id,source_type="asset")
    post_transaction(payer_cashbox_id,"OUT",cost,"asset_purchase",created_by_id,f"شراء أصل: {name}",document.id,"asset",code)
    row=Asset(asset_code=code,name=name,category=category,acquisition_cost=cost,acquisition_date=acquisition_date,payer_cashbox_id=payer_cashbox_id,custodian_user_id=custodian_user_id,location=location,notes=notes,document_id=document.id)
    db.session.add(row)
    db.session.flush()
    document.source_id=str(row.id)
    if create_tank:
        number=FuelTank.query.count()+1
        while FuelTank.query.filter_by(code=f"TANK-{number:04d}").first(): number+=1
        tank=FuelTank(name=name,code=f"TANK-{number:04d}",capacity_liters=tank_capacity_liters or None,location=location,is_active=True,notes=notes)
        db.session.add(tank)
        db.session.flush()
        row.tank_id=tank.id
    from .accounting import post_asset
    post_asset(row,created_by_id)
    return row
