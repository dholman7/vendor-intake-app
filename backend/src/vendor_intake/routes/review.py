from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vendor_intake.db import Role, User
from vendor_intake.deps import get_session, get_today, require_roles
from vendor_intake.schemas import ExtractionOut, ReviewDecision, ReviewQueueItem
from vendor_intake.services import review

router = APIRouter(tags=["review"])
reviewer = require_roles(Role.REVIEWER, Role.ADMIN)


@router.get("/review-queue")
def review_queue(
    user: User = Depends(reviewer), session: Session = Depends(get_session)
) -> list[ReviewQueueItem]:
    return review.review_queue(session, user.tenant_id)


@router.post("/extractions/{extraction_id}/decision")
def decide(
    extraction_id: str,
    body: ReviewDecision,
    user: User = Depends(reviewer),
    session: Session = Depends(get_session),
    today: date = Depends(get_today),
) -> ExtractionOut:
    return review.decide(
        session,
        user,
        extraction_id,
        approve=body.decision == "approve",
        note=body.note,
        today=today,
    )
