import argparse
import asyncio
from getpass import getpass

from app.modules.users.application.use_cases.manage_users import (
    UserAlreadyExistsError,
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


def main() -> None:
    args = _arguments()
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    try:
        asyncio.run(_create_user(args.email, args.role, password))
    except (UserAlreadyExistsError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
