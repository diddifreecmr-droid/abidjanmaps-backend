import argparse
import asyncio
from getpass import getpass

from app.modules.users.application.use_cases.manage_users import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserService,
)
from app.modules.users.infrastructure.persistence.user_repository import (
    SQLAlchemyUserRepository,
)
from app.modules.users.infrastructure.security.jwt_token_service import JWTTokenService
from app.modules.users.infrastructure.security.password_hasher import Argon2PasswordHasher
from app.shared.configuration.settings import settings
from app.shared.infrastructure.db import async_session_factory


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an AbidjanMaps user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("user", "admin"), default="user")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset the password for an existing user instead of creating one.",
    )
    return parser.parse_args()


async def _create_user(email: str, role: str, password: str) -> None:
    async with async_session_factory() as session:
        service = UserService(
            repository=SQLAlchemyUserRepository(session),
            password_hasher=Argon2PasswordHasher(),
            token_service=JWTTokenService(
                secret_key=settings.auth_secret_key,
                algorithm=settings.auth_algorithm,
                expire_minutes=settings.auth_token_expire_minutes,
            ),
        )
        user = await service.create_user(
            email=email,
            password=password,
            role=role,
        )
        print(f"User created: id={user.id} email={user.email} role={user.role}")


async def _reset_password(email: str, password: str) -> None:
    async with async_session_factory() as session:
        service = UserService(
            repository=SQLAlchemyUserRepository(session),
            password_hasher=Argon2PasswordHasher(),
            token_service=JWTTokenService(
                secret_key=settings.auth_secret_key,
                algorithm=settings.auth_algorithm,
                expire_minutes=settings.auth_token_expire_minutes,
            ),
        )
        user = await service.reset_password(email=email, password=password)
        print(f"Password reset: id={user.id} email={user.email} role={user.role}")


def main() -> None:
    args = _arguments()
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    try:
        if args.reset_password:
            asyncio.run(_reset_password(args.email, password))
        else:
            asyncio.run(_create_user(args.email, args.role, password))
    except (UserAlreadyExistsError, UserNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
