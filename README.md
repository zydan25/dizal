# Dizal — نظام إدارة وتشغيل مشروع توزيع الديزل

Dizal هو نظام إداري وتشغيلي ومحاسبي داخلي لمشروع توزيع الديزل.

الفكرة الأساسية: المستخدم لا يحتاج إلى فهم المحاسبة حتى يستخدم النظام. الواجهة تتحدث بلغة التشغيل اليومية مثل: رأس المال، صندوقي، الديزل الموجود، المزارعون، المديونية، المقبوض، المتبقي، المتوقع، التسوية والربح. أما الخلفية فتدير الحركات المالية والمخزنية وسجل التدقيق.

## الحالة الحالية

مرحلة المشروع الحالية هي مرحلة التوصيف والتصميم المعماري فقط.

تم اعتماد التوجه التالي:
- Flask / Python
- PostgreSQL
- SQLAlchemy
- Flask-Migrate / Alembic
- Flask-Security-Too مع RBAC وصلاحيات دقيقة
- Blueprints منفصلة
- تنظيم Domain Modules قريب من أسلوب تطبيقات Django
- Bootstrap RTL + CSS مخصص
- Mobile-First PWA
- واجهة مختلفة حسب دور المستخدم
- WhatsApp Provider Adapter
- سندات وتقارير وطباعة
- سجل تدقيق وحركات مالية ومخزنية غير قابلة للتلاعب بالحذف المباشر

لم يبدأ بعد تنفيذ الوظائف النهائية اعتمادًا على هذه الوثائق. هذه الوثائق هي المرجع قبل كتابة الكود التشغيلي.

## بيئة الإنتاج المستهدفة

~~~text
GitHub repository: zydan25/dizal
Application path: /home/root/projects/dizal
Database: dizal
Database user: dizal
Database password: dizal  (قيمة إعداد أولي ويجب تغييرها في الإنتاج)
Bind address: 127.0.0.1
Port: 4012
Domain: dizal.alattab.site
Process manager: PM2
Reverse proxy: Nginx
~~~

## الوثائق

- docs/SPECIFICATION.md — توصيف النظام الكامل.
- docs/ARCHITECTURE.md — البنية البرمجية.
- docs/DATA_MODEL.md — نماذج البيانات والعلاقات.
- docs/BUSINESS_RULES.md — قواعد العمل والحسابات.
- docs/ROLES_PERMISSIONS.md — الأدوار والصلاحيات.
- docs/UI_SPEC.md — مواصفات واجهة الهاتف وERP Navigation.
- docs/REPORTS_AND_DOCUMENTS.md — التقارير والسندات والطباعة.
- docs/WHATSAPP.md — تكامل واتساب.
- docs/IMPLEMENTATION_PLAN.md — مراحل التنفيذ.
- docs/DEPLOYMENT.md — إعداد الخادم والنشر.
- docs/TEST_PLAN.md — الاختبارات ومعايير القبول.
- docs/OPEN_DECISIONS.md — النقاط التي يجب أن تبقى قابلة للضبط.

## المبدأ الحاسم

لا يتم اختصار المشروع إلى CRUD.

كل عملية مؤثرة على المال أو المخزون يجب أن تمر عبر خدمة أعمال واضحة وتنتج:
1. حركة مالية عند الحاجة.
2. حركة مخزنية عند الحاجة.
3. رقم مستند.
4. سجل تدقيق.
5. حالة اعتماد.
6. إشعار عند الحاجة.
7. إمكانية إصدار سند أو كشف مرتبط بها.

القيود المحاسبية التفصيلية تبقى خلف الكواليس، بينما المستخدم يرى نتيجة العملية بلغة بسيطة.
