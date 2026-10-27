from collections.abc import Callable, Iterator
from datetime import date

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from vendor_intake.config import Settings
from vendor_intake.db import Role, User
from vendor_intake.errors import AppError
from vendor_intake.repositories.users import UserRepository
from vendor_intake.security import decode_token
from vendor_intake.services.storage import LocalStorage

SESSION_COOKIE = "session"


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_storage(request: Request) -> LocalStorage:
    storage: LocalStorage = request.app.state.storage
    return storage


def get_today(request: Request) -> date:
    """Injected so date rules (insurance expiry) can be tested against a fixed day."""
    today: Callable[[], date] = request.app.state.today
    return today()


def _token_from(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, credentials = header.partition(" ")
    if scheme.lower() == "bearer" and credentials:
        return credentials
    return request.cookies.get(SESSION_COOKIE)


def current_user(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    token = _token_from(request)
    if token is None:
        raise AppError(401, "not_authenticated", "Sign in to continue")
    claims = decode_token(token, settings.jwt_secret)
    user = UserRepository(session).get(claims["sub"], claims["tid"]) if claims else None
    if user is None:
        raise AppError(401, "invalid_session", "Your session is invalid or has expired")
    return user


def require_roles(*roles: Role) -> Callable[..., User]:
    def _dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden", "Your role does not allow this action")
        return user

    return _dependency
