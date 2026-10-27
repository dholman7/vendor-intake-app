from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from vendor_intake.config import Settings
from vendor_intake.db import DocumentKind, User
from vendor_intake.deps import current_user, get_session, get_settings, get_storage
from vendor_intake.errors import not_found
from vendor_intake.repositories.documents import DocumentRepository, ExtractionRepository
from vendor_intake.schemas import DocumentOut, ExtractionOut
from vendor_intake.services import documents, vendors
from vendor_intake.services.review import extraction_out
from vendor_intake.services.storage import LocalStorage

router = APIRouter(tags=["documents"])


@router.post("/vendors/{vendor_id}/documents", status_code=201)
async def upload_document(
    vendor_id: str,
    request: Request,
    background: BackgroundTasks,
    kind: DocumentKind = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    storage: LocalStorage = Depends(get_storage),
) -> DocumentOut:
    vendor = vendors.get_vendor(session, vendor_id, user.tenant_id)
    # Read one byte past the limit so oversize files are detected without buffering them whole.
    data = await file.read(settings.max_upload_bytes + 1)
    content_type = documents.validate_upload(
        file.filename or "", file.content_type, len(data), settings.max_upload_bytes
    )
    document = documents.upload_document(
        session,
        storage,
        user,
        vendor,
        kind=kind,
        filename=file.filename or "upload",
        content_type=content_type,
        data=data,
    )
    background.add_task(
        documents.process_document,
        request.app.state.session_factory,
        storage,
        document.id,
        user.tenant_id,
        settings.extraction_delay_seconds,
    )
    return DocumentOut.model_validate(document)


@router.get("/vendors/{vendor_id}/documents")
def list_documents(
    vendor_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> list[DocumentOut]:
    vendor = vendors.get_vendor(session, vendor_id, user.tenant_id)
    return [
        DocumentOut.model_validate(d)
        for d in DocumentRepository(session).for_vendor(vendor.id, user.tenant_id)
    ]


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> DocumentOut:
    document = DocumentRepository(session).get(document_id, user.tenant_id)
    if document is None:
        raise not_found("document")
    return DocumentOut.model_validate(document)


@router.get("/documents/{document_id}/extraction")
def get_extraction(
    document_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> ExtractionOut:
    document = DocumentRepository(session).get(document_id, user.tenant_id)
    if document is None:
        raise not_found("document")
    extraction = ExtractionRepository(session).for_document(document.id, user.tenant_id)
    if extraction is None:
        raise not_found("extraction")
    return extraction_out(extraction, DocumentKind(document.kind))
