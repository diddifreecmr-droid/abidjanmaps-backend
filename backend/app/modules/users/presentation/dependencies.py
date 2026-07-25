from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.application.use_cases.manage_users import UserService
from app.modules.users.domain.entities.user import User
from app.modules.users.infrastructure.persistence.user_repository import (
    SQLAlchemyUserRepository,
)
from app.modules.users.infrastructure.security.jwt_token_service import JWTTokenService
from app.modules.users.infrastructure.security.password_hasher import Argon2PasswordHasher
from app.shared.configuration.settings import settings
from app.shared.infrastructure.db import get_async_session


bearer_scheme = HTTPBearer(auto_error=False)


def build_token_service() -> JWTTokenService:
    return JWTTokenService(
        secret_key=settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
        expire_minutes=settings.auth_token_expire_minutes,
    )


def get_user_service(
    session: AsyncSession = Depends(get_async_session),
) -> UserService:
    return UserService(
        repository=SQLAlchemyUserRepository(session),
        password_hasher=Argon2PasswordHasher(),
        token_service=build_token_service(),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    claims = build_token_service().decode(credentials.credentials)
    if claims is None:
        raise unauthorized
    user = await SQLAlchemyUserRepository(session).get_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user
