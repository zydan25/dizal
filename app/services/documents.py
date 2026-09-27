from datetime import date
from ..extensions import db
from ..models import Document,ProjectSequence

PREFIXES={"CAP":"CAP","TRF":"TRF","AST":"AST","SUP":"SUP","DOC":"DOC"}

def next_document_number(document_type):
    year=date.today().year
    row=ProjectSequence.query.filter_by(document_type=document_type,year=year).first()
    if not row:
        row=ProjectSequence(document_type=document_type,year=year,last_number=0)
        db.session.add(row)
        db.session.flush()
    row.last_number+=1
    prefix=PREFIXES.get(document_type,document_type.upper())
    return f"{prefix}-{year}-{row.last_number:06d}"

def create_document(document_type,title,created_by_id,source_type=None,source_id=None,notes=None,approved_by_id=None,status="approved"):
    number=next_document_number(document_type)
    document=Document(number=number,document_type=document_type,title=title,created_by_id=created_by_id,approved_by_id=approved_by_id,source_type=source_type,source_id=str(source_id) if source_id else None,notes=notes,status=status)
    db.session.add(document)
    db.session.flush()
    return document
