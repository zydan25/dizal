# Dizal Phase 1 — Foundation

## Status
تم تنفيذ Foundation على branch: feature/phase1-foundation.

## Included
- Flask Application Factory.
- SQLAlchemy.
- Flask-Migrate integration.
- Flask-Security-Too.
- Argon2.
- Roles/permissions/user overrides.
- Audit Log.
- Health endpoint.
- Project Settings.
- Theme engine.
- Branding upload foundation.
- Arabic RTL mobile-first shell.
- ERP tree navigation.
- Desktop sidebar + mobile drawer.
- Mobile bottom navigation.
- PWA manifest/service worker.
- Authentication.
- Error pages.
- Seed.
- CI.
- Smoke tests.

## Intentionally deferred
- Capital and employee custody.
- Cashboxes and movements.
- Assets.
- Fuel supply and stock.
- Farmers and approvals.
- Dispensing and collections.
- Settlements.
- Profit engine.
- Reports and print documents.
- WhatsApp adapter.

هذه العناصر لها تصميم وتوثيق مسبق في Phase 0، وسيتم بناؤها فوق Foundation بدل خلطها في أول مرحلة.

## Acceptance
لا تنتقل المرحلة التالية قبل:
- نجاح CI.
- عمل login.
- عمل RBAC.
- عمل /health.
- عمل migration.
- عمل PWA shell.
- عمل theme.
