from app.modules.users.application.ports.password_hasher import PasswordHasher
from app.modules.users.application.ports.token_service import TokenService
from app.modules.users.application.ports.user_repository import UserRepository
from app.modules.users.domain.entities.user import User, normalize_email


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        role: str = "user",
    ) -> User:
        normalized_email = normalize_email(email)
        if len(password) < 10:
            raise ValueError("Password must contain at least 10 characters")
        if await self.repository.get_by_email(normalized_email) is not None:
            raise UserAlreadyExistsError("A user with this email already exists")

        return await self.repository.create(
            User(email=normalized_email, role=role),
            self.password_hasher.hash(password),
        )

    async def authenticate(self, *, email: str, password: str) -> tuple[User, str]:
        stored = await self.repository.get_by_email(normalize_email(email))
        if stored is None:
            raise InvalidCredentialsError("Invalid email or password")
        user, password_hash = stored
        if not user.is_active or not self.password_hasher.verify(password, password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        if user.id is None:
            raise RuntimeError("Persisted user has no identifier")
        return user, self.token_service.create(user.id, user.role)

    async def list_users(self) -> list[User]:
        return await self.repository.list_all()
