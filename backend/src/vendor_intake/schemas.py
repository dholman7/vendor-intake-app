from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from vendor_intake.db import (
    DocumentKind,
    DocumentStatus,
    ExtractionStatus,
    Role,
    VendorCategory,
    VendorStatus,
)

VendorName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    # Plain string: a malformed address is just another failed sign-in, not a 422.
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class TenantOut(ApiModel):
    id: str
    name: str


class UserOut(ApiModel):
    id: str
    email: str
    name: str
    role: Role
    tenant: TenantOut


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - a scheme name, not a secret
    user: UserOut


class VendorCreate(BaseModel):
    name: VendorName
    category: VendorCategory
    contact_email: EmailStr


class VendorUpdate(BaseModel):
    name: VendorName | None = None
    category: VendorCategory | None = None
    contact_email: EmailStr | None = None


class VendorOut(ApiModel):
    id: str
    name: str
    category: VendorCategory
    contact_email: str
    status: VendorStatus
    flags: list[str]
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VendorPage(BaseModel):
    items: list[VendorOut]
    total: int
    limit: int
    offset: int


class DocumentOut(ApiModel):
    id: str
    vendor_id: str
    kind: DocumentKind
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime


class FieldOut(BaseModel):
    value: str | None
    confidence: float


class ExtractionOut(ApiModel):
    id: str
    document_id: str
    kind: DocumentKind
    fields: dict[str, FieldOut]
    status: ExtractionStatus
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]
    # validate_default: an omitted note must still trip the reject rule below.
    note: str | None = Field(default=None, max_length=1000, validate_default=True)

    @field_validator("note")
    @classmethod
    def _reject_needs_note(cls, note: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("decision") == "reject" and not (note and note.strip()):
            raise ValueError("A note is required when rejecting")
        return note.strip() if note else note


class ReviewQueueItem(BaseModel):
    vendor_id: str
    vendor_name: str
    submitted_at: datetime | None
    lowest_confidence: float
    extractions: list[ExtractionOut]


class ActorOut(ApiModel):
    id: str
    name: str
    email: str


class AuditEventOut(BaseModel):
    id: int
    action: str
    actor: ActorOut
    at: datetime
    details: dict[str, object]


class AuditTrail(BaseModel):
    items: list[AuditEventOut]
