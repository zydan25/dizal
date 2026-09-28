from datetime import datetime,date,timezone
from ..extensions import db

class ProjectSequence(db.Model):
    __tablename__="project_sequence"
    id=db.Column(db.Integer,primary_key=True)
    document_type=db.Column(db.String(40),nullable=False)
    year=db.Column(db.Integer,nullable=False)
    last_number=db.Column(db.Integer,nullable=False,default=0)
    __table_args__=(db.UniqueConstraint("document_type","year",name="uq_sequence_type_year"),)

class Document(db.Model):
    __tablename__="document"
    id=db.Column(db.Integer,primary_key=True)
    number=db.Column(db.String(60),unique=True,nullable=False,index=True)
    document_type=db.Column(db.String(40),nullable=False,index=True)
    title=db.Column(db.String(180),nullable=False)
    issue_date=db.Column(db.Date,nullable=False,default=date.today)
    status=db.Column(db.String(25),nullable=False,default="approved")
    source_type=db.Column(db.String(60),nullable=True,index=True)
    source_id=db.Column(db.String(80),nullable=True,index=True)
    created_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    approved_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=True)
    notes=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    created_by=db.relationship("User",foreign_keys=[created_by_id])
    approved_by=db.relationship("User",foreign_keys=[approved_by_id])

class DocumentAttachment(db.Model):
    __tablename__="document_attachment"
    id=db.Column(db.Integer,primary_key=True)
    document_id=db.Column(db.Integer,db.ForeignKey("document.id",ondelete="CASCADE"),nullable=False,index=True)
    original_name=db.Column(db.String(250),nullable=False)
    storage_key=db.Column(db.String(500),nullable=False)
    mime_type=db.Column(db.String(120),nullable=True)
    size_bytes=db.Column(db.BigInteger,nullable=True)
    sha256=db.Column(db.String(64),nullable=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
    document=db.relationship("Document",backref=db.backref("attachments",cascade="all, delete-orphan"))
