from .permissions import user_has_permission

SECTIONS=[
{"key":"home","title":"الرئيسية","icon":"bi-grid-1x2","items":[("dashboard.index","لوحة المتابعة","bi-speedometer2","dashboard.view")]},
{"key":"operations","title":"التشغيل","icon":"bi-fuel-pump","items":[
    ("fuel.supply","التوريدات","bi-truck","fuel.supply.create"),
    ("fuel.stock","المخزون","bi-boxes","fuel.stock.view"),
    ("fuel.tanks","الخزانات","bi-fuel-pump-fill","fuel.tank.manage"),
    ("sales.dispense","صرف الديزل","bi-droplet-fill","fuel.dispense"),
    ("sales.point_of_sale","نقطة بيع عامة","bi-shop","fuel.dispense")
]},
{"key":"farmers","title":"المزارعون","icon":"bi-people","items":[
    ("farmers.index","المزارعون","bi-person-lines-fill","farmers.view"),
    ("farmers.pending","بانتظار المراجعة","bi-hourglass-split","farmers.approve"),
    ("sales.payment","التحصيل","bi-cash-coin","farmer.payment.create")
]},
{"key":"money","title":"المال والصندوق","icon":"bi-wallet2","items":[
    ("cashbox.index","الصناديق","bi-cash-stack","cashbox.view"),
    ("capital.index","رأس المال","bi-bank","capital.view"),
    ("assets.index","الأصول","bi-building","assets.view"),
    ("expenses.index","المصروفات","bi-receipt","expenses.manage"),
    ("settlements.index","التسويات","bi-arrow-left-right","settlement.manage")
]},
{"key":"reports","title":"التقارير","icon":"bi-bar-chart","items":[
    ("reports.index","ملخص التقارير","bi-file-earmark-bar-graph","reports.view"),
    ("reports.farmers_debts","ديون المزارعين","bi-person-exclamation","reports.view"),
    ("reports.employees","أداء الموظفين","bi-person-badge","reports.view"),
    ("reports.sales_report_view","تقرير المبيعات","bi-graph-up-arrow","reports.view"),
    ("reports.dispense_report_view","تقرير صرف الديزل","bi-droplet-half","reports.view"),
    ("documents.index","السندات","bi-receipt-cutoff","documents.view"),
    ("reports.my_statement","كشف حسابي","bi-file-earmark-text","employee.statement.view"),
    ("reports.my_operations","تقريري التشغيلي","bi-clipboard-data","employee.statement.view")
]},
{"key":"admin","title":"الإدارة","icon":"bi-sliders2","items":[
    ("employees.index","الموظفون","bi-person-gear","users.view"),
    ("roles.index","الأدوار والصلاحيات","bi-shield-lock","roles.manage"),
    ("audit.index","سجل التدقيق","bi-journal-check","audit.view"),
    ("notifications.index","الإشعارات","bi-bell","notifications.view"),
    ("whatsapp.index","واتساب","bi-whatsapp","whatsapp.manage"),
    ("settings.index","إعدادات المشروع","bi-gear","settings.manage")
]},
]

def build_navigation(user):
    result=[]
    for section in SECTIONS:
        items=[]
        for endpoint,label,icon,permission in section["items"]:
            if endpoint=="reports.my_statement" and not user.is_employee:
                continue
            if user_has_permission(user,permission):
                items.append({"endpoint":endpoint,"label":label,"icon":icon})
        if items:
            result.append({**section,"items":items})
    return result
