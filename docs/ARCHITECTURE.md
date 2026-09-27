# Dizal — البنية المعمارية

## 1. المبدأ العام

المشروع Flask لكنه منظم بأسلوب قريب من تطبيقات Django:
- Application Factory.
- Domain Modules.
- Blueprints.
- Models منفصلة منطقيًا.
- Services لقواعد الأعمال.
- Repositories للاستعلامات المعقدة عند الحاجة.
- Forms للتحقق من المدخلات.
- Permissions مستقلة.
- Templates وStatic منظمة حسب المجال.

## 2. الهيكل المقترح

~~~text
dizal/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── config.py
│   ├── cli.py
│   │
│   ├── models/
│   │   ├── security.py
│   │   ├── project.py
│   │   ├── employees.py
│   │   ├── capital.py
│   │   ├── assets.py
│   │   ├── cashbox.py
│   │   ├── fuel.py
│   │   ├── farmers.py
│   │   ├── sales.py
│   │   ├── payments.py
│   │   ├── accounting.py
│   │   ├── documents.py
│   │   ├── notifications.py
│   │   ├── whatsapp.py
│   │   ├── audit.py
│   │   └── __init__.py
│   │
│   ├── blueprints/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── employees/
│   │   ├── capital/
│   │   ├── assets/
│   │   ├── cashbox/
│   │   ├── fuel/
│   │   ├── farmers/
│   │   ├── collections/
│   │   ├── settlements/
│   │   ├── reports/
│   │   ├── documents/
│   │   ├── notifications/
│   │   ├── whatsapp/
│   │   └── settings/
│   │
│   ├── services/
│   │   ├── accounting/
│   │   ├── cashbox/
│   │   ├── fuel/
│   │   ├── farmers/
│   │   ├── settlements/
│   │   ├── documents/
│   │   ├── notifications/
│   │   ├── whatsapp/
│   │   └── reports/
│   │
│   ├── repositories/
│   ├── forms/
│   ├── permissions/
│   ├── utils/
│   ├── templates/
│   └── static/
│
├── migrations/
├── tests/
├── docs/
├── deploy/
├── scripts/
├── instance/
├── wsgi.py
└── requirements.txt
~~~

## 3. فصل المسؤوليات

### Blueprint
مسؤول عن:
- استقبال HTTP.
- قراءة النموذج.
- استدعاء Service.
- إعادة النتيجة للواجهة.

لا يحتوي على الحسابات المالية المعقدة.

### Service
مسؤول عن:
- قواعد العمل.
- التحقق من الحدود.
- إنشاء الحركات.
- تنفيذ Transaction واحدة.
- إنشاء Journal Entries.
- إصدار المستند.

### Repository
يستخدم فقط عندما يصبح الاستعلام:
- معقدًا.
- متكررًا.
- يحتاج تجميعات.
- يحتاج تقارير متعددة الجداول.

لا نستخدم Repository لكل استعلام بسيط بلا داعٍ.

### Model
يمثل البيانات والعلاقات والقيود البسيطة.

لا نضع دورة عمل كاملة داخل property ضخمة في Model.

## 4. قاعدة البيانات

PostgreSQL في الإنتاج.

SQLAlchemy هو ORM وطبقة الاستعلام الأساسية.

العمليات الحساسة تستخدم database transaction.

المبدأ:
- commit واحد لكل عملية أعمال كاملة.
- rollback عند أي فشل.
- لا يتم تعديل رصيد يدوي.

## 5. Accounting Engine

محرك محاسبي داخلي بسيط وقابل للتوسع.

الحركات تنتج قيودًا مزدوجة متوازنة.

الأمثلة:

### إيداع رأس مال
مدين: نقدية/حساب
دائن: رأس مال المالك

### تسليم للموظف
مدين: عهدة موظف
دائن: نقدية المشروع

### شراء ديزل
مدين: مخزون ديزل
دائن: عهدة الموظف

### بيع نقدي
مدين: عهدة الموظف
دائن: مبيعات

وبالتزامن:
مدين: تكلفة مبيعات
دائن: مخزون ديزل

### بيع آجل
مدين: ذمم المزارعين
دائن: مبيعات

وبالتزامن يتم إخراج تكلفة الديزل من المخزون.

### تحصيل
مدين: صندوق الموظف
دائن: ذمم المزارع

هذه أمثلة تصميمية وستخضع للمراجعة المحاسبية النهائية.

## 6. Transaction Integrity

عمليات مثل اعتماد التوريد يجب أن تكون داخل transaction واحدة:
- تحديث حالة التوريد.
- إضافة حركة المخزون.
- إضافة الحركة المالية.
- تحديث العهدة.
- إنشاء السند.
- إنشاء audit log.
- إرسال notification outbox event.

لا نريد عملية تنفذ نصفها ثم يفشل النصف الآخر.

## 7. الملفات

لا تحفظ ملفات المستخدم باسمها الحقيقي كمرجع تخزين.

يحفظ:
- UUID.
- SHA-256.
- MIME type.
- الحجم.
- اسم العرض.
- نوع المستند.
- صاحب المستند.
- تاريخ الرفع.

التخزين المبدئي:
instance/uploads/YYYY/MM/...

لاحقًا يمكن نقل Storage إلى S3-compatible دون تغيير Domain Logic.

## 8. Cache وJobs

لا نحتاج Redis في النسخة الأولى إذا لم يكن ضروريًا.

يمكن استخدام:
- Flask-Caching لاحقًا.
- Scheduler/queue بسيط لواتساب.
- PostgreSQL outbox للعمليات المهمة.

عند الحاجة الفعلية للتوسع يمكن إضافة Redis + RQ/Celery.

## 9. PWA

الواجهة server-rendered في البداية لأنها:
- أبسط.
- أسرع في التطوير.
- مناسبة لنظام إداري.
- أسهل في الطباعة.
- ممتازة مع Flask.

PWA توفر:
- manifest.
- service worker.
- installable app.
- cached shell.
- app-like navigation.

المعاملات المالية لا تسمح بالحفظ Offline في النسخة الأولى لتجنب ازدواج الحركات.

## 10. Security

- Flask-Security-Too.
- Argon2.
- CSRF.
- Secure cookies.
- Permission decorators.
- Server-side authorization.
- Audit log.
- Upload validation.
- Rate limits لاحقًا.
- Secret management عبر Environment.

الأهم:
إخفاء الرابط من القائمة ليس حماية. يجب أن يحمي الـRoute نفسه بالصلاحية.

## 11. التوسعة

يجب أن يكون من السهل إضافة:
- أكثر من موظف.
- أكثر من مخزن.
- أكثر من خزان.
- أكثر من نقطة توزيع.
- بنك.
- تحويلات.
- سيارات.
- مصروفات.
- موردين.
- فواتير.
- أكثر من طريقة تسعير.

لكن النسخة الأولى لا تبالغ في إدخال التعقيد إذا لم يخدم المشروع.
