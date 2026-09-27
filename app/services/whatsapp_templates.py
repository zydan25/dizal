DEFAULT_TEMPLATES=[
("farmer_approved","اعتماد مزارع","تم اعتماد المزارع {{name}} في مشروع {{project}}."),
("farmer_changes","استكمال بيانات مزارع","يرجى استكمال بيانات المزارع {{name}}: {{note}}"),
("supply_approved","اعتماد توريد","تم اعتماد توريد الديزل رقم {{document}} بكمية {{liters}} لتر."),
("payment_received","سداد","تم تسجيل سداد {{amount}} من المزارع {{name}}."),
("settlement_due","تسوية موظف","حان موعد مراجعة تسوية الموظف {{name}} للفترة {{period}}.")
]

def seed_templates(db_session):
    from ..models import WhatsAppTemplate
    for key,title,body in DEFAULT_TEMPLATES:
        row=WhatsAppTemplate.query.filter_by(key=key).first()
        if not row:
            db_session.add(WhatsAppTemplate(key=key,title=title,body=body,enabled=True))
    db_session.flush()
