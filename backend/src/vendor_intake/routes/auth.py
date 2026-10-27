from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from vendor_intake.config import Settings
from vendor_intake.db import User
from vendor_intake.deps import SESSION_COOKIE, current_user, get_session, get_settings
from vendor_intake.errors import AppError
from vendor_intake.repositories.users import UserRepository
from vendor_intake.schemas import LoginRequest, LoginResponse, TenantOut, UserOut
from vendor_intake.security import check_credentials, issue_token

router = APIRouter(tags=["auth"])


def _user_out(session: Session, user: User) -> UserOut:
    tenant = UserRepository(session).tenant(user.tenant_id)
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        tenant=TenantOut.model_validate(tenant),
    )


@router.post("/auth/login")
def login(
    body: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = UserRepository(session).by_email(str(body.email))
    if not check_credentials(user, body.password) or user is None:
        raise AppError(401, "invalid_credentials", "Email or password is incorrect")
    token = issue_token(user, settings.jwt_secret, settings.jwt_ttl_minutes)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.jwt_ttl_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return LoginResponse(access_token=token, user=_user_out(session, user))


@router.post("/auth/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")


@router.get("/me")
def me(user: User = Depends(current_user), session: Session = Depends(get_session)) -> UserOut:
    return _user_out(session, user)
