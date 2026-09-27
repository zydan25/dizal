# Dizal Status

## Phase 0 — Specification
مكتملة.

## Phase 1 — Foundation
منفذة على feature/phase1-foundation:
- Flask Factory
- SQLAlchemy
- Flask-Migrate
- Flask-Security-Too
- RBAC
- Audit
- Theme
- PWA
- ERP Navigation
- Login
- Settings

## Phase 2 — Finance Core
منفذة على نفس الفرع:
- Employees
- Employee Profile
- Cashboxes
- Cashbox transactions
- Central capital
- Employee capital allocation
- Documents/sequences
- Assets
- Finance UI
- Phase 2 tests

## المرحلة التالية
Phase 3:
- التوريد.
- الخزانات.
- مخزون اللترات.
- تكلفة اللتر.
- اعتماد المدير.
- مرفقات التوريد.

## الجودة
الـCI موجود ويشغل:
- compileall
- migration generation
- migration upgrade
- pytest

حالة تشغيل CI يجب التحقق منها عبر GitHub Actions قبل الدمج النهائي إلى main.
