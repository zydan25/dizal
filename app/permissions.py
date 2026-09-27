PERMISSIONS={
"dashboard.view":("لوحة المتابعة","dashboard"),
"settings.view":("مشاهدة الإعدادات","settings"),"settings.manage":("إدارة الإعدادات","settings"),
"users.view":("مشاهدة المستخدمين","users"),"users.manage":("إدارة المستخدمين","users"),"roles.manage":("إدارة الأدوار والصلاحيات","users"),
"audit.view":("مشاهدة سجل التدقيق","audit"),
"notifications.view":("مشاهدة الإشعارات","notifications"),"theme.manage":("إدارة الثيم","settings"),
"employees.view":("مشاهدة الموظفين","employees"),"employees.manage":("إدارة الموظفين","employees"),
"cashbox.view":("مشاهدة الصندوق","cashbox"),"cashbox.view_all":("مشاهدة جميع الصناديق","cashbox"),
"capital.view":("مشاهدة رأس المال","capital"),"capital.create":("إضافة رأس المال","capital"),"capital.allocate":("تسليم رأس المال للموظف","capital"),
"assets.view":("مشاهدة الأصول","assets"),"assets.create":("إضافة أصل","assets"),
"fuel.supply.create":("رفع توريد ديزل","fuel"),"fuel.supply.approve":("اعتماد توريد ديزل","fuel"),"fuel.stock.view":("مشاهدة مخزون الديزل","fuel"),"fuel.tank.manage":("إدارة خزانات الديزل","fuel"),
"fuel.dispense":("صرف الديزل","fuel"),"fuel.price.override":("تغيير سعر البيع عند الصرف","fuel"),
"farmers.view":("مشاهدة المزارعين","farmers"),"farmers.view_all":("مشاهدة جميع المزارعين","farmers"),"farmers.create":("إضافة مزارع","farmers"),"farmers.documents.upload":("رفع مرفقات المزارع","farmers"),"farmers.approve":("اعتماد المزارعين","farmers"),"farmers.quota.change":("تعديل سقف المزارع","farmers"),"farmer.payment.create":("تسجيل سداد مزارع","farmers"),
"expenses.manage":("إدارة المصروفات","expenses"),"settlement.manage":("إدارة التسويات","settlements"),"settlement.approve":("اعتماد التسويات","settlements"),
"reports.view":("مشاهدة التقارير","reports"),"documents.view":("مشاهدة السندات","documents"),
}
ROLE_PERMISSIONS={"manager":set(PERMISSIONS.keys()),"employee":{"dashboard.view","cashbox.view","fuel.supply.create","fuel.stock.view","fuel.dispense","farmers.view","farmers.create","farmers.documents.upload","farmer.payment.create"}}
def user_has_permission(user,permission_key):
    if not user or not user.is_authenticated:return False
    if user.has_role("manager"):return True
    overrides={item.permission_key:item.allowed for item in user.permission_overrides}
    if permission_key in overrides:return overrides[permission_key]
    allowed=set()
    for role in user.roles:allowed.update(link.permission.key for link in role.permission_links)
    return permission_key in allowed
