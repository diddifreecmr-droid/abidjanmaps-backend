from dataclasses import dataclass
from datetime import datetime


USER_ROLES = frozenset({"user", "admin"})


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("A valid email address is required")
    return email


@dataclass(frozen=True, kw_only=True)
class User:
    email: str
    role: str = "user"
    is_active: bool = True
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "email", normalize_email(self.email))
        if self.role not in USER_ROLES:
            raise ValueError(f"Unsupported user role: {self.role}")
