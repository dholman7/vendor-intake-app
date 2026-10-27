from sqlalchemy import select
from sqlalchemy.orm import Session

from vendor_intake.db import Document, DocumentKind, Extraction


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, document: Document) -> None:
        self.session.add(document)
        self.session.flush()

    def get(self, document_id: str, tenant_id: str) -> Document | None:
        return self.session.scalar(
            select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
        )

    def for_vendor(self, vendor_id: str, tenant_id: str) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document)
                .where(Document.vendor_id == vendor_id, Document.tenant_id == tenant_id)
                .order_by(Document.created_at, Document.id)
            )
        )

    def latest_by_kind(self, vendor_id: str, tenant_id: str) -> dict[DocumentKind, Document]:
        """Most recent upload per kind; a re-upload supersedes earlier documents."""
        latest: dict[DocumentKind, Document] = {}
        for doc in self.for_vendor(vendor_id, tenant_id):
            latest[DocumentKind(doc.kind)] = doc
        return latest


class ExtractionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, extraction: Extraction) -> None:
        self.session.add(extraction)
        self.session.flush()

    def get(self, extraction_id: str, tenant_id: str) -> Extraction | None:
        return self.session.scalar(
            select(Extraction).where(
                Extraction.id == extraction_id, Extraction.tenant_id == tenant_id
            )
        )

    def for_document(self, document_id: str, tenant_id: str) -> Extraction | None:
        return self.session.scalar(
            select(Extraction).where(
                Extraction.document_id == document_id, Extraction.tenant_id == tenant_id
            )
        )
