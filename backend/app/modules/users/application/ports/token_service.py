from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    role: str


class TokenService(ABC):
    @abstractmethod
    def create(self, user_id: int, role: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def decode(self, token: str) -> TokenClaims | None:
        raise NotImplementedError
