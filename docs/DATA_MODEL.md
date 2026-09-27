# Dizal — نموذج البيانات

هذه الوثيقة تحدد الكيانات الأساسية قبل بناء SQLAlchemy Models.

## 1. Security

### User
- id
- username
- phone
- email
- password hash
- display name
- active
- created_at
- last_login_at

### Role
- id
- name
- label
- description

### Permission
- id
- key
- label
- module

### UserRole
ربط المستخدم بالأدوار.

### RolePermission
ربط الدور بالصلاحيات.

### UserPermissionOverride
صلاحية إضافية أو منع صلاحية لمستخدم محدد عند الحاجة.

## 2. Project

### ProjectSettings
- اسم المشروع.
- العملة.
- اللترات في الدبة.
- الأسعار الافتراضية.
- الحدود.
- الألوان.
- الخط.
- الشعار.
- توقيع المدير.
- إعدادات السندات.

### ProjectSequence
لتوليد الأرقام:
- document_type
- year
- last_number

## 3. Employees

### EmployeeProfile
- user_id
- employee_code
- hire_date
- salary_type
- salary_value
- farmer_limit_override
- credit_limit_override
- daily_liters_limit_override
- quota_change_permission
- status

### EmployeeAssignment
يحدد ما يملكه الموظف من:
- مزارعين.
- مخازن.
- نقاط توزيع.
- صناديق.

## 4. Capital

### CapitalContribution
- date
- amount
- source
- description
- document
- status
- approved_by

### CapitalAllocation
يسجل توزيع رأس المال:
- contribution_id
- allocation_type
- amount
- employee_id
- asset_id
- supply_id
- notes

## 5. Assets

### Asset
- asset_code
- name
- category
- acquisition_cost
- acquisition_date
- location
- custodian_user
- status
- document

### AssetMovement
- asset_id
- movement_type
- from_location
- to_location
- from_employee
- to_employee
- reason

## 6. Cashbox

### Cashbox
- name
- type
- owner_user
- status

### CashboxTransaction
- cashbox_id
- direction
- transaction_type
- amount
- reference_type
- reference_id
- description
- posted_by
- created_at

### EmployeeCustody
للقيمة الإجمالية التي تقع تحت مسؤولية الموظف مع التفصيل الناتج من الحركات.

## 7. Fuel

### FuelTank
- name
- capacity_liters
- location
- custodian
- active

### FuelPurchase
- supplier
- date
- liters
- diesel_amount
- delivery_fee
- other_fee
- landed_cost
- unit_cost
- employee
- tank
- status

### FuelStockMovement
- tank_id
- movement_type
- liters
- unit_cost
- source_type
- source_id
- created_by

### FuelAdjustment
للتالف أو النقص أو الجرد.

## 8. Farmer

### Farmer
- code
- name
- phone
- address
- status
- quota_drums
- credit_limit_drums
- assigned_employee
- notes

### FarmerDocument
- farmer
- document_type
- original_name
- storage_key
- checksum
- uploaded_by

### FarmerQuotaMovement
لتاريخ تعديل السقف.

## 9. Sales / Dispensing

### FuelDispense
- document_number
- farmer
- employee
- tank
- liters
- drums
- sale_price_per_liter
- total_amount
- paid_amount
- credit_amount
- payment_mode
- status

### DispenseLine
إذا تطورت العمليات لاحقًا إلى أكثر من منتج أو أكثر من سعر.

## 10. Receivables

### FarmerAccount
حساب المزارع.

### FarmerPayment
- document_number
- farmer
- employee
- amount
- payment_method
- date
- reference
- notes

### ReceivableAllocation
لربط السداد بالفواتير/الصرف عند الحاجة.

## 11. Settlement

### EmployeeSettlement
- employee
- period
- expected_cash
- expected_stock_cost
- expected_receivables
- actual_cash
- shortage
- overage
- salary
- owner_transfer
- retained_operating_capital
- status

## 12. Accounting

### Account
دليل الحسابات.

### JournalEntry
- date
- source_type
- source_id
- document_number
- description

### JournalLine
- journal_entry
- account
- debit
- credit
- employee
- farmer
- project
- cost_center

## 13. Documents

### Document
- document_number
- document_type
- source_type
- source_id
- title
- issue_date
- created_by
- approved_by
- status

### DocumentAttachment
- document_id
- object_type
- object_id
- file_key
- original_name
- sha256
- mime_type
- size

## 14. Notifications

### Notification
- user
- type
- title
- body
- severity
- read_at
- link

### NotificationPreference
ما إذا كان المستخدم يريد:
- داخل النظام.
- واتساب.
- الاثنين.

## 15. WhatsApp

### WhatsAppConfig
- provider
- enabled
- endpoint
- encrypted_token
- sender

### WhatsAppMessage
- recipient
- type
- body
- attachment
- status
- provider_message_id
- retry_count
- error
- sent_at

## 16. Audit

### AuditLog
- actor_user_id
- action
- object_type
- object_id
- before_json
- after_json
- ip_address
- user_agent
- request_id
- created_at

## 17. مبادئ العلاقات

- مزارع واحد يمكن أن يملك عددًا كبيرًا من الصرفيات.
- مزارع واحد يمكن أن يملك عددًا كبيرًا من السداد.
- موظف واحد يملك صندوقًا أو أكثر مستقبلًا.
- موظف واحد قد يدير مجموعة مزارعين.
- توريد واحد يؤثر في المخزون بعد الاعتماد.
- كل حركة مالية يمكن أن ترتبط بمستند.
- كل حركة حساسة لها Audit Log.
