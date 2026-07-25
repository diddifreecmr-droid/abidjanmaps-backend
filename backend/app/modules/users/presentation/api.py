from fastapi import APIRouter, Depends, HTTPException

from app.modules.users.application.use_cases.manage_users import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserService,
)
from app.modules.users.domain.entities.user import User
from app.modules.users.presentation.dependencies import (
    get_current_user,
    get_user_service,
    require_admin,
)
from app.modules.users.presentation.schemas import (
    LoginSchema,
    TokenResponseSchema,
    UserCreateSchema,
    UserReadSchema,
)
from app.shared.configuration.settings import settings


router = APIRouter(tags=["users"])


def _user_response(user: User) -> UserReadSchema:
    if user.id is None:
        raise RuntimeError("Persisted user has no identifier")
    return UserReadSchema(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/auth/login", response_model=TokenResponseSchema)
async def login(
    payload: LoginSchema,
    service: UserService = Depends(get_user_service),
) -> TokenResponseSchema:
    try:
        _, token = await service.authenticate(
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponseSchema(
        access_token=token,
        expires_in_seconds=settings.auth_token_expire_minutes * 60,
    )


@router.get("/users/me", response_model=UserReadSchema)
async def current_user(user: User = Depends(get_current_user)) -> UserReadSchema:
    return _user_response(user)


@router.post("/users", response_model=UserReadSchema, status_code=201)
async def create_user(
    payload: UserCreateSchema,
    _: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> UserReadSchema:
    try:
        user = await service.create_user(
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _user_response(user)


@router.get("/users", response_model=list[UserReadSchema])
async def list_users(
    _: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> list[UserReadSchema]:
    return [_user_response(user) for user in await service.list_users()]
