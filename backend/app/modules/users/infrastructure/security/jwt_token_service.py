from datetime import datetime, timedelta, timezone

import jwt

from app.modules.users.application.ports.token_service import TokenClaims, TokenService


class JWTTokenService(TokenService):
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        expire_minutes: int,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create(self, user_id: int, role: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)
        return jwt.encode(
            {"sub": str(user_id), "role": role, "exp": expires_at},
            self.secret_key,
            algorithm=self.algorithm,
        )

    def decode(self, token: str) -> TokenClaims | None:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return TokenClaims(
                user_id=int(payload["sub"]),
                role=str(payload["role"]),
            )
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            return None
