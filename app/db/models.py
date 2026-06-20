import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = sa.Column(sa.String, nullable=False)
    plan = sa.Column(sa.String, nullable=False, default="free")
    api_key_hash = sa.Column(sa.String, nullable=True, unique=False)
    created_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_tenants_name", "name"),
    )

class Document(Base):
    __tablename__ = "documents"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True)
    filename = sa.Column(sa.String, nullable=False)
    page_count = sa.Column(sa.Integer, nullable=False, default=0)
    chunk_count = sa.Column(sa.Integer, nullable=False, default=0)
    ingested_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_documents_tenant_filename", "tenant_id", "filename"),
    )

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = sa.Column(UUID(as_uuid=True), nullable=False, index=True)
    query_hash = sa.Column(sa.String, nullable=False)
    cache_hit = sa.Column(sa.Boolean, default=False)
    retrieval_ms = sa.Column(sa.Integer, default=0)
    llm_ms = sa.Column(sa.Integer, default=0)
    hallucination_score = sa.Column(sa.Float, default=0.0)
    created_at = sa.Column(sa.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_audit_tenant_created", "tenant_id", "created_at"),
    )
