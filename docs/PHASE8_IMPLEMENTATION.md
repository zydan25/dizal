# Dizal Phase 8 — الإدارة والإشعارات وواتساب

## ما تم تنفيذه
- إدارة إعدادات المشروع والثيم والهوية.
- رفع شعار المشروع وتوقيع المدير.
- Protected media access للهوية.
- Employee edit.
- Employee operating limits overrides.
- Per-user permission overrides.
- Role permission matrix.
- Notification model and notification center.
- Audit center.
- WhatsApp config.
- WhatsApp templates.
- WhatsApp outbox/queue.
- Generic HTTP/Baileys/Cloud provider selection foundation.
- Retry status.
- PM2 worker لتفريغ الرسائل.

## نموذج واتساب
النظام لا يستدعي مزود واتساب من كل Route. الرسالة تدخل جدول WhatsAppMessage بحالة queued، ثم يلتقطها worker ويرسلها.

## الأمان
Token لا يظهر كاملًا في واجهة الإعدادات. ملفات الشعار والتوقيع لا تُقدم كملفات عامة من Nginx بل من Route محمي.

## المرحلة التالية
Phase 9: hardening, backups, health/monitoring, deployment validation, regression cleanup, final acceptance.
