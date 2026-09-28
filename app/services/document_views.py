from ..models import Document,CapitalContribution,CapitalAllocation,Asset,FuelPurchase,FuelDispense,FarmerPayment,OperatingExpense,EmployeeSettlement,Farmer

def source_for_document(document):
    if not document.source_type or not document.source_id:
        return None
    ident=int(document.source_id)
    if document.source_type=="document_reversal":
        return Document.query.get(ident)
    mapping={
        "capital":CapitalContribution,"capital_allocation":CapitalAllocation,"asset":Asset,
        "fuel_purchase":FuelPurchase,"fuel_dispense":FuelDispense,"farmer_payment":FarmerPayment,
        "operating_expense":OperatingExpense,"employee_settlement":EmployeeSettlement,
        "farmer":Farmer
    }
    model=mapping.get(document.source_type)
    return model.query.get(ident) if model else None

def get_document(document_id):
    document=Document.query.get_or_404(document_id)
    return document,source_for_document(document)
