PERMISSIONS = {
    "dashboard.view": ("لوحة المتابعة", "dashboard"),
    "settings.view": ("مشاهدة الإعدادات", "settings"),
    "settings.manage": ("إدارة الإعدادات", "settings"),
    "users.view": ("مشاهدة المستخدمين", "users"),
    "users.manage": ("إدارة المستخدمين", "users"),
    "roles.manage": ("إدارة الأدوار والصلاحيات", "users"),
    "audit.view": ("مشاهدة سجل التدقيق", "audit"),
    "theme.manage": ("إدارة الثيم", "settings"),
}

ROLE_PERMISSIONS = {
    "manager": set(PERMISSIONS.keys()),
    "employee": {"dashboard.view"},
}

def user_has_permission(user, permission_key):
    if not user or not user.is_authenticated:
        return False
    if user.has_role("manager"):
        return True
    overrides = {item.permission_key: item.allowed for item in user.permission_overrides}
    if permission_key in overrides:
        return overrides[permission_key]
    allowed = set()
    for role in user.roles:
        allowed.update(link.permission.key for link in role.permission_links)
    return permission_key in allowed
