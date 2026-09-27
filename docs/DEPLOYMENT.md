# Dizal — خطة النشر

## 1. الخادم

المسار:

/home/root/projects/dizal

## 2. PostgreSQL

القيم المستهدفة مبدئيًا:

- DB: dizal
- User: dizal
- Password: dizal

هذه قيمة إعداد أولي فقط، وتحتاج إلى تغييرها في بيئة الإنتاج ووضعها في Secret/Environment.

## 3. Python

بيئة افتراضية داخل:

/home/root/projects/dizal/.venv

## 4. Application server

Gunicorn على:

127.0.0.1:4012

## 5. PM2

اسم العملية:
dizal

PM2 يطلق Gunicorn ويعيد تشغيله عند الحاجة.

## 6. Nginx

Nginx يستقبل:
https://dizal.alattab.site

ويمرر إلى:
http://127.0.0.1:4012

مع:
- X-Forwarded-Proto.
- X-Forwarded-For.
- Host.
- Upload size limit.

## 7. TLS

بعد صحة DNS:
- Certbot.
- Redirect HTTP → HTTPS.

## 8. الملفات

Uploads:
instance/uploads

يجب ألا تكون الملفات الحساسة متاحة مباشرة عبر URL public.

Access يكون عبر Route محمي بالصلاحية.

## 9. Migrations

الإنتاج:
flask db upgrade

ولا يتم:
create_all

في بيئة الإنتاج.

## 10. Backup

الحد الأدنى:
- Backup PostgreSQL يومي.
- الاحتفاظ بعدد نسخ متدرج.
- اختبار Restore.
- Backup للملفات.

## 11. Logs

ثلاث طبقات:
- Nginx.
- PM2/Gunicorn.
- Application audit.

## 12. Health endpoint

سنضيف:
GET /health

ويرجع حالة:
- app.
- database.
- version.

## 13. deploy script

المراحل:
1. git pull.
2. activate venv.
3. pip install.
4. migration.
5. tests.
6. PM2 reload.
7. nginx config test.
8. health check.

إذا فشل health check بعد deploy، لا نعلن النجاح.

## 14. Security

- لا نضع secrets داخل Git.
- لا نضع token واتساب في logs.
- لا نسمح بتنفيذ ملفات مرفوعة.
- نتحقق من MIME والامتداد والحجم.
- نستخدم secure cookies في HTTPS.

## 15. Domain

dizal.alattab.site

يحتاج:
- A record إلى الخادم.
- ثم TLS.
