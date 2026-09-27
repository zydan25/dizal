from ..models import Document,CapitalContribution,CapitalAllocation,Asset,FuelPurchase,FuelDispense,FarmerPayment,OperatingExpense,EmployeeSettlement

def source_for_document(document):
    if not document.source_type or not document.source_id:
        return None
    ident=int(document.source_id)
    mapping={
        "capital":CapitalContribution,"capital_allocation":CapitalAllocation,"asset":Asset,
        "fuel_purchase":FuelPurchase,"fuel_dispense":FuelDispense,"farmer_payment":FarmerPayment,
        "operating_expense":OperatingExpense,"employee_settlement":EmployeeSettlement
    }
    model=mapping.get(document.source_type)
    return model.query.get(ident) if model else None

def get_document(document_id):
    document=Document.query.get_or_404(document_id)
    return document,source_for_document(document)
