# Dizal — نظام إدارة وتوزيع الديزل

نظام إداري ومحاسبي مبسط لمشروع توزيع الديزل، مبني بـ Flask + PostgreSQL + SQLAlchemy + Flask-Migrate، مع واجهات عربية RTL مصممة Mobile-First وPWA.

## المبدأ
النظام يخفي التعقيد المحاسبي عن المستخدم. المستخدم يرى:
- صندوق الموظف
- الديزل الموجود والمتبقي
- المزارعين وحدودهم
- التوريدات المعلقة والمقبولة
- المقبوضات والديون
- الأرباح المتوقعة والفعلية
- السندات والتقارير

بينما يحتفظ الخلفية بسجل مالي ومخزني قابل للتدقيق.

## بيئة الإنتاج المخططة
- المشروع: `/home/root/projects/dizal`
- النطاق: `dizal.alattab.site`
- المنفذ: `4012`
- PostgreSQL database: `dizal`
- PostgreSQL user: `dizal`
- PM2 process: `dizal`

راجع:
- `docs/ARCHITECTURE.md`
- `docs/BUSINESS_RULES.md`
- `docs/ROADMAP.md`
- `deploy/`
- `scripts/`

> كلمة مرور PostgreSQL الافتراضية في إعداد الخادم هي `dizal` كما طلب المشروع، ويجب تغييرها في بيئة الإنتاج عند اعتماد النظام.
