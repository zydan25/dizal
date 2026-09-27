# Dizal — خطة التنفيذ المرحلية

## المرحلة 0 — التوصيف

الحالة:
مطلوبة الآن.

المخرجات:
- Specification.
- Architecture.
- Data Model.
- Business Rules.
- Roles.
- UI Spec.
- Reports.
- WhatsApp.
- Deployment.
- Test Plan.
- Open Decisions.

معيار الانتهاء:
وجود وثائق مترابطة وعدم وجود قاعدة أعمال أساسية مجهولة.

## المرحلة 1 — Foundation

نبني:
- Flask App Factory.
- PostgreSQL connection.
- SQLAlchemy.
- Flask-Migrate.
- Flask-Security-Too.
- Roles/Permissions.
- Error pages.
- CSRF.
- Base layout.
- Theme engine.
- PWA shell.
- ERP Tree Navigation.
- Audit framework.

اختبار النهاية:
Login يعمل، RBAC يعمل، migration تعمل، PWA تفتح.

## المرحلة 2 — Project / Employees / Cashboxes

نبني:
- المشروع.
- المدير.
- الموظفون.
- الصناديق.
- تسليم رأس المال.
- سند تسليم.
- كشف الصندوق.

اختبار النهاية:
المدير ينشئ موظفًا ويسلمه رأس مال ويظهر في كشف الموظف.

## المرحلة 3 — Capital / Assets

نبني:
- رأس المال.
- تخصيص رأس المال.
- الأصول.
- مستندات الأصل.
- نقل العهدة.

اختبار النهاية:
يمكن تسجيل 1,230,000 ثم توزيعها على أصل وديزل ورسوم.

## المرحلة 4 — Fuel Supply / Stock

نبني:
- التوريدات.
- المرفقات.
- الموافقات.
- خزانات.
- حركة المخزون.
- تكلفة اللتر.
- الجرد.

اختبار النهاية:
توريد معلق لا يغير المخزون، وبعد الاعتماد يغير المخزون والصندوق في transaction واحدة.

## المرحلة 5 — Farmers

نبني:
- المزارعين.
- المرفقات.
- العقود.
- الاعتماد.
- السقوف.
- التعيين للموظف.

اختبار النهاية:
موظف لا يستطيع صرف لمزارع معلق أو تجاوز سقف.

## المرحلة 6 — Dispense / Collections

نبني:
- الصرف.
- النقد/الدين.
- التحصيل.
- كشف المزارع.
- السندات.

اختبار النهاية:
3 دباب اليوم + 2 دبة لاحقًا + سداد جزئي يعكس الأرصدة بشكل صحيح.

## المرحلة 7 — Settlements / Profit

نبني:
- التسوية.
- الرصيد المتوقع.
- الفعلي.
- الراتب.
- التحويل للمدير.
- الربح.

اختبار النهاية:
يمكن إنهاء فترة لموظف وإظهار كامل الفروقات.

## المرحلة 8 — Reports / Printing

نبني:
- كل التقارير.
- PDF.
- Print CSS.
- Export.

## المرحلة 9 — WhatsApp / Notifications

نبني:
- Provider Adapter.
- Queue.
- Templates.
- Logs.
- Retry.
- Webhooks.

## المرحلة 10 — UI Polish

نعيد المرور على كل الشاشات:
- 360.
- 390.
- 412.
- Tablet.
- Desktop.

مع:
- Empty.
- Loading.
- Error.
- Accessibility.
- Safe Area.

## المرحلة 11 — Security / Audit

- مراجعة الصلاحيات.
- مراجعة uploads.
- Audit كامل.
- Session security.
- Rate limiting.
- Secrets.
- Backup.
- Restore test.

## المرحلة 12 — Production

- Linux.
- PostgreSQL.
- Nginx.
- TLS.
- PM2.
- Health check.
- Logs.
- Backup.
- Deploy script.

## استراتيجية Git

الاقتراح:
- main = النسخة القابلة للنشر.
- feature branches لكل مرحلة.
- PR لكل مرحلة.
- CI قبل الدمج.

في مرحلة التوصيف الحالية يسمح commit مباشر إلى main لأن المستودع جديد، وبعد بدء البرمجة نحافظ على branches.
