from .permissions import user_has_permission

SECTIONS=[
 {"key":"home","title":"الرئيسية","icon":"bi-grid-1x2","items":[("dashboard.index","لوحة المتابعة","bi-speedometer2","dashboard.view")]},
 {"key":"operations","title":"التشغيل","icon":"bi-fuel-pump","items":[("dashboard.index","التشغيل","bi-fuel-pump","dashboard.view")]},
 {"key":"farmers","title":"المزارعون","icon":"bi-people","items":[("dashboard.index","المزارعون","bi-person-lines-fill","dashboard.view")]},
 {"key":"money","title":"المال والصندوق","icon":"bi-wallet2","items":[("cashbox.index","الصندوق","bi-cash-stack","cashbox.view"),("capital.index","رأس المال","bi-bank","capital.view"),("assets.index","الأصول","bi-building","assets.view")]},
 {"key":"reports","title":"التقارير","icon":"bi-bar-chart","items":[("dashboard.index","التقارير","bi-file-earmark-bar-graph","dashboard.view")]},
 {"key":"admin","title":"الإدارة","icon":"bi-sliders2","items":[("employees.index","الموظفون","bi-person-gear","employees.view"),("settings.index","إعدادات المشروع","bi-gear","settings.view")]},
]

def build_navigation(user):
    result=[]
    for section in SECTIONS:
        items=[]
        for endpoint,label,icon,permission in section["items"]:
            if user_has_permission(user,permission):
                items.append({"endpoint":endpoint,"label":label,"icon":icon})
        if items:
            result.append({**section,"items":items})
    return result
