from abc import ABC, abstractmethod

from app.modules.users.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User, password_hash: str) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> tuple[User, str] | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[User]:
        raise NotImplementedError
