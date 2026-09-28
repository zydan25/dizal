# Dizal — نظام إدارة وتشغيل مشروع توزيع الديزل

Dizal نظام إداري وتشغيلي ومحاسبي داخلي لمشروع توزيع الديزل، مصمم ليكون سهل الاستخدام من الهاتف ويعرض للمستخدم لغة التشغيل اليومية بدل المصطلحات المحاسبية المعقدة.

## الحالة الحالية

تم بناء أساس النظام ووحدات Finance/Fuel/Farmers/Sales/Collections/Accounting/Settlements/Reports/Documents/RBAC/Notifications/WhatsApp.

المرحلة الحالية هي Integration + UI Completion + Acceptance:
- ربط جميع الـBlueprints الموجودة.
- استكمال الـNavigation.
- مركز السندات والطباعة وPDF والمشاركة.
- العكس والتصحيح دون حذف العمليات المعتمدة.
- استكمال دورات المزارعين والتوريدات والتسويات.
- تحسين لوحة التشغيل للهاتف.
- اختبارات Regression وCI فعلي قبل الدمج.

## المبدأ الحاسم

لا يتم اختصار النظام إلى CRUD.

كل عملية مؤثرة على المال أو المخزون تمر عبر خدمة أعمال واضحة وتنتج عند الحاجة:
1. حركة مالية.
2. حركة مخزنية.
3. رقم مستند.
4. سجل تدقيق.
5. حالة اعتماد.
6. إشعار.
7. سند أو كشف مرتبط.

العملية المعتمدة لا تُحذف ولا تُعدّل تاريخيًا مباشرة؛ التصحيح يكون عبر عكس موثق أو Adjustment وفق صلاحية وقواعد المشروع.

## التقنية

- Flask / Python
- PostgreSQL
- SQLAlchemy
- Flask-Migrate / Alembic
- Flask-Security-Too + RBAC
- Bootstrap RTL + CSS مخصص
- Mobile-First PWA
- WhatsApp Provider Adapter
- سندات وتقارير وطباعة/PDF
- Audit Log

## الوثائق

- docs/SPECIFICATION.md
- docs/ARCHITECTURE.md
- docs/DATA_MODEL.md
- docs/BUSINESS_RULES.md
- docs/ROLES_PERMISSIONS.md
- docs/UI_SPEC.md
- docs/REPORTS_AND_DOCUMENTS.md
- docs/WHATSAPP.md
- docs/TEST_PLAN.md
- docs/UI_INTEGRATION_AUDIT.md
