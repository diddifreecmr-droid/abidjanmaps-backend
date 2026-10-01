import hashlib
import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.shared.configuration.settings import settings


service_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ServiceClient:
    client_id: str
    service_name: str
    scopes: frozenset[str] = frozenset()


def _service_auth_error(
    *,
    status_code: int = 401,
    code: str = "authentication_required",
    message: str = "Service authentication required",
) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
        },
        headers=headers,
    )


def _claim_scopes(claims: dict) -> frozenset[str]:
    raw = claims.get("scope", "")
    if isinstance(raw, str):
        return frozenset(scope for scope in raw.split() if scope)
    if isinstance(raw, list):
        return frozenset(str(scope) for scope in raw)
    return frozenset()


def _service_name_from_claims(claims: dict) -> str:
    raw_service_name = claims.get("service_name") or claims.get("service")
    if isinstance(raw_service_name, str) and raw_service_name.strip():
        return raw_service_name.strip()
    subject = str(claims.get("sub", ""))
    if subject.startswith("service:"):
        return subject.split(":", 1)[1]
    return subject


def decode_identity_service_token(
    token: str,
    *,
    x_client_id: str,
    required_scopes: frozenset[str],
    expected_service_name: str | None = None,
) -> ServiceClient:
    if not settings.identity_jwks_url:
        raise _service_auth_error()
    try:
        signing_key = PyJWKClient(
            settings.identity_jwks_url,
            cache_keys=True,
            lifespan=3600,
        ).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.identity_issuer,
            audience=settings.diddimap_service_audience,
            options={
                "require": ["exp", "iat", "sub", "iss", "aud", "scope", "token_type"],
            },
        )
    except (PyJWKClientConnectionError, PyJWKClientError, jwt.InvalidTokenError) as exc:
        raise _service_auth_error(
            code="service_token_invalid",
            message="Service token invalid",
        ) from exc

    if claims.get("role") != "service" or claims.get("token_type") != "service":
        raise _service_auth_error(code="service_token_invalid", message="Service token invalid")
    if claims.get("status") != "active":
        raise _service_auth_error(
            status_code=403,
            code="service_token_inactive",
            message="Service token inactive",
        )
    if claims.get("client_id") != x_client_id:
        raise _service_auth_error(
            code="service_client_id_invalid",
            message="X-Client-ID does not match service token",
        )

    service_name = _service_name_from_claims(claims)
    if expected_service_name is not None and service_name != expected_service_name:
        raise _service_auth_error(
            status_code=403,
            code="service_not_allowed",
            message="Service is not allowed for this integration",
        )

    scopes = _claim_scopes(claims)
    if not required_scopes.issubset(scopes):
        raise _service_auth_error(
            status_code=403,
            code="service_scope_invalid",
            message="Service token scope is insufficient",
        )

    return ServiceClient(client_id=x_client_id, service_name=service_name, scopes=scopes)


def _require_legacy_diddigo_service_client(
    *,
    token: str,
    x_client_id: str,
) -> ServiceClient:
    expected_client_id = settings.diddigo_service_client_id
    expected_token_hash = settings.diddigo_service_token_sha256
    if not expected_client_id or not expected_token_hash:
        raise _service_auth_error()

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(x_client_id, expected_client_id):
        raise _service_auth_error()
    if not hmac.compare_digest(token_hash, expected_token_hash.lower()):
        raise _service_auth_error()

    return ServiceClient(
        client_id=x_client_id,
        service_name="diddigo",
        scopes=frozenset({"diddimap:traces:write"}),
    )


async def _authenticate_service_client(
    *,
    credentials: HTTPAuthorizationCredentials | None,
    x_client_id: str | None,
    required_scope: str,
    expected_service_name: str | None = None,
    allow_legacy_diddigo: bool = False,
) -> ServiceClient:
    if credentials is None or x_client_id is None:
        raise _service_auth_error()

    token = credentials.credentials
    identity_error: HTTPException | None = None
    if settings.identity_jwks_url:
        try:
            return decode_identity_service_token(
                token,
                x_client_id=x_client_id,
                required_scopes=frozenset({required_scope}),
                expected_service_name=expected_service_name,
            )
        except HTTPException as exc:
            identity_error = exc

    if allow_legacy_diddigo:
        try:
            return _require_legacy_diddigo_service_client(
                token=token,
                x_client_id=x_client_id,
            )
        except HTTPException:
            pass

    if identity_error is not None and identity_error.status_code == 403:
        raise identity_error
    raise _service_auth_error()


def require_service_client(
    *,
    required_scope: str,
    expected_service_name: str | None = None,
):
    async def _dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(service_bearer_scheme),
        x_client_id: Annotated[str | None, Header(alias="X-Client-ID")] = None,
    ) -> ServiceClient:
        return await _authenticate_service_client(
            credentials=credentials,
            x_client_id=x_client_id,
            required_scope=required_scope,
            expected_service_name=expected_service_name,
        )

    return _dependency


async def require_diddigo_service_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(service_bearer_scheme),
    x_client_id: Annotated[str | None, Header(alias="X-Client-ID")] = None,
) -> ServiceClient:
    return await _authenticate_service_client(
        credentials=credentials,
        x_client_id=x_client_id,
        required_scope="diddimap:traces:write",
        expected_service_name="diddigo",
        allow_legacy_diddigo=True,
    )
