# Dizal — خطة الاختبارات

## 1. Unit Tests

اختبارات الخدمات:
- تحويل دبة إلى لتر.
- حساب سقف المزارع.
- حساب تكلفة اللتر.
- حساب الدين.
- حساب الرصيد.
- حساب الاحتياج.
- حساب الربح.
- حساب التسوية.

## 2. Model Tests

- القيود.
- unique.
- foreign keys.
- default values.

## 3. Permission Tests

اختبار أن:
- الموظف لا يصل للإدارة.
- الموظف لا يعتمد.
- الموظف لا يرى موظفًا آخر.
- الموظف لا يتجاوز نطاق مزارعيه.
- المدير يستطيع كل ما تسمح به الصلاحيات.

## 4. Workflow Tests

### Farmer
submitted → approved
submitted → rejected
submitted → changes_requested

### Supply
draft → submitted → approved
submitted → changes_requested
submitted → rejected

### Settlement
draft → approved
approved لا يعدل مباشرة.

## 5. Accounting Tests

كل JournalEntry:
مجموع Debit = مجموع Credit.

ولا توجد حركة مالية بدون مصدر.

## 6. Inventory Tests

- لا stock negative.
- التوريد المعلق لا يزيد المخزون.
- الاعتماد يزيد المخزون مرة واحدة.
- reverse يعكس الحركة.
- الجرد ينشئ adjustment.

## 7. Cashbox Tests

- لا سحب أكبر من الرصيد.
- الإيداع يظهر.
- التحصيل يظهر.
- التوريد المعتمد يخصم.
- التسوية تطابق الحركات.

## 8. Farmer Debt Tests

مثال:
3 دباب × 20 = 60 لتر.

إذا السعر 650:
القيمة = 39,000.

دفع 10,000:
الدين = 29,000.

## 9. UI Tests

نختبر:
- 360x800.
- 390x844.
- 412x915.
- Tablet.
- Desktop.

## 10. PWA Tests

- manifest.
- install.
- service worker.
- cache shell.
- no broken route after refresh.

## 11. Upload Tests

- الصور.
- PDF.
- الحجم.
- MIME.
- اسم الملف.
- checksum.
- authorization.

## 12. WhatsApp Tests

- queue.
- success.
- failure.
- retry.
- provider timeout.
- invalid token.
- webhook signature.

## 13. Regression

كل مرحلة جديدة تشغل:
- unit.
- integration.
- permissions.
- migration check.

## 14. Definition of Done

لا تعتبر الميزة مكتملة حتى يوجد:
- UI.
- Backend.
- Permission.
- Validation.
- Service.
- Audit.
- Test.
- Empty/Error states.
- documentation.
