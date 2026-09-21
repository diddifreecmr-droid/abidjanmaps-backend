import hashlib
import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.shared.configuration.settings import settings


service_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ServiceClient:
    client_id: str
    service_name: str


async def require_diddigo_service_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(service_bearer_scheme),
    x_client_id: Annotated[str | None, Header(alias="X-Client-ID")] = None,
) -> ServiceClient:
    unauthorized = HTTPException(
        status_code=401,
        detail={
            "code": "authentication_required",
            "message": "Service authentication required",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )
    expected_client_id = settings.diddigo_service_client_id
    expected_token_hash = settings.diddigo_service_token_sha256
    if (
        credentials is None
        or x_client_id is None
        or not expected_client_id
        or not expected_token_hash
    ):
        raise unauthorized

    token_hash = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(x_client_id, expected_client_id):
        raise unauthorized
    if not hmac.compare_digest(token_hash, expected_token_hash.lower()):
        raise unauthorized

    return ServiceClient(client_id=x_client_id, service_name="diddigo")
