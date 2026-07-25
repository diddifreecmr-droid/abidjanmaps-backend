from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.application.ports.user_repository import UserRepository
from app.modules.users.domain.entities.user import User, normalize_email
from app.modules.users.infrastructure.persistence.models import UserORM


def _to_domain(orm: UserORM) -> User:
    return User(
        id=orm.id,
        email=orm.email,
        role=orm.role,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User, password_hash: str) -> User:
        orm = UserORM(
            email=user.email,
            password_hash=password_hash,
            role=user.role,
            is_active=user.is_active,
        )
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return _to_domain(orm)

    async def get_by_email(self, email: str) -> tuple[User, str] | None:
        result = await self.session.execute(
            select(UserORM).where(UserORM.email == normalize_email(email))
        )
        orm = result.scalar_one_or_none()
        return (_to_domain(orm), orm.password_hash) if orm is not None else None

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(UserORM).where(UserORM.id == user_id))
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm is not None else None

    async def update_password(self, email: str, password_hash: str) -> User | None:
        result = await self.session.execute(
            select(UserORM).where(UserORM.email == normalize_email(email))
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None

        orm.password_hash = password_hash
        await self.session.commit()
        await self.session.refresh(orm)
        return _to_domain(orm)

    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(UserORM).order_by(UserORM.id))
        return [_to_domain(orm) for orm in result.scalars().all()]
