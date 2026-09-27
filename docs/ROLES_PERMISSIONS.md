# Dizal — الأدوار والصلاحيات

## 1. الأدوار الابتدائية

### manager
إدارة كاملة.

### employee
تشغيل مقيد.

يمكن إضافة:
- auditor
- supervisor
- accountant
لاحقًا دون إعادة بناء النظام.

## 2. صلاحيات المدير

أمثلة:
- dashboard.view
- users.view
- users.manage
- roles.manage
- settings.manage
- capital.create
- capital.approve
- assets.view
- assets.create
- fuel.purchase.create
- fuel.purchase.approve
- fuel.stock.view
- fuel.adjust
- farmers.view
- farmers.create
- farmers.approve
- farmers.suspend
- farmers.change_quota
- dispense.view
- dispense.create
- payment.view
- payment.create
- cashbox.view
- cashbox.transfer
- settlement.create
- settlement.approve
- reports.view
- reports.export
- documents.print
- whatsapp.manage
- audit.view

## 3. صلاحيات الموظف

الأساس:
- dashboard.view
- farmers.view
- farmers.create
- farmers.documents.upload
- fuel.stock.view
- fuel.purchase.create
- dispense.create
- payment.create
- cashbox.view
- documents.view_own
- reports.view_own
- notifications.view

## 4. قواعد إضافية

الصلاحية ليست بديلًا عن نطاق البيانات.

مثال:
الموظف لديه farmers.view
لكن يرى فقط المزارعين المعينين له.

المدير لديه farmers.view
فيرى الجميع.

## 5. Override

يمكن إعطاء موظف محدد:
- صلاحية إضافية.
- أو استثناء من صلاحية.

ويتم تسجيل هذا في Audit.

## 6. واجهة الصلاحيات

المدير يرى شاشة منظمة حسب الوحدات:

التشغيل
  التوريد
  الصرف
  التحصيل

المزارعون
  عرض
  إضافة
  اعتماد
  تعديل سقف

المال
  الصندوق
  التحويل
  التسوية

الإدارة
  الموظفون
  الصلاحيات
  الإعدادات
  واتساب

لا تعرض هذه الشاشة للموظف.
