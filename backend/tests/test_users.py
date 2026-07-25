import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.modules.users.application.use_cases.manage_users import (
    InvalidCredentialsError,
    UserService,
)
from app.modules.users.domain.entities.user import User
from app.modules.users.infrastructure.security.jwt_token_service import JWTTokenService
from app.modules.users.infrastructure.security.password_hasher import Argon2PasswordHasher
from app.modules.users.presentation.dependencies import (
    get_current_user,
    get_user_service,
)


client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides.clear()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_password_is_hashed_and_verified_with_argon2() -> None:
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash("a-secure-password")

    assert password_hash != "a-secure-password"
    assert password_hash.startswith("$argon2")
    assert hasher.verify("a-secure-password", password_hash) is True
    assert hasher.verify("wrong-password", password_hash) is False


def test_user_service_can_reset_password() -> None:
    class FakeHasher:
        def hash(self, password: str) -> str:
            return f"hashed:{password}"

        def verify(self, password: str, password_hash: str) -> bool:
            return password_hash == f"hashed:{password}"

    class FakeTokenService:
        def create(self, user_id: int, role: str) -> str:
            return f"token:{user_id}:{role}"

        def decode(self, token: str):
            return None

    class FakeRepository:
        def __init__(self) -> None:
            self.password_hash = "old-hash"

        async def create(self, user: User, password_hash: str) -> User:
            raise AssertionError("create should not be called")

        async def get_by_email(self, email: str):
            return User(id=9, email=email, role="admin"), self.password_hash

        async def get_by_id(self, user_id: int) -> User | None:
            return User(id=user_id, email="admin@example.com", role="admin")

        async def update_password(self, email: str, password_hash: str) -> User | None:
            self.password_hash = password_hash
            return User(id=9, email=email, role="admin")

        async def list_all(self) -> list[User]:
            return []

    repository = FakeRepository()
    service = UserService(
        repository=repository,
        password_hasher=FakeHasher(),
        token_service=FakeTokenService(),
    )

    user = asyncio.run(
        service.reset_password(
            email="ADMIN@example.com",
            password="new-password-123",
        )
    )

    assert user.email == "admin@example.com"
    assert repository.password_hash == "hashed:new-password-123"


def test_jwt_round_trip_preserves_identity_and_role() -> None:
    tokens = JWTTokenService(
        secret_key="test-secret-that-is-long-enough-for-hs256",
        algorithm="HS256",
        expire_minutes=5,
    )

    token = tokens.create(user_id=42, role="admin")
    claims = tokens.decode(token)

    assert claims is not None
    assert claims.user_id == 42
    assert claims.role == "admin"
    assert tokens.decode(f"{token}invalid") is None


def test_business_write_requires_authentication() -> None:
    response = client.post(
        "/api/v1/roads",
        json={
            "name": "Protected road",
            "geometry": {
                "type": "LineString",
                "coordinates": [[-4.02, 5.33], [-3.99, 5.34]],
            },
            "surface_state": "good",
            "seasonal_practicability": "all_year",
        },
    )

    assert response.status_code == 401


def test_regular_user_cannot_validate_business_data() -> None:
    async def regular_user() -> User:
        return User(id=7, email="agent@example.com", role="user")

    app.dependency_overrides[get_current_user] = regular_user

    response = client.post("/api/v1/roads/1/validate")

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator role required"


def test_login_returns_a_bearer_token() -> None:
    class FakeUserService:
        async def authenticate(self, *, email: str, password: str):
            assert email == "admin@example.com"
            assert password == "correct-password"
            return (
                User(id=1, email=email, role="admin"),
                "signed-test-token",
            )

    app.dependency_overrides[get_user_service] = lambda: FakeUserService()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ADMIN@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "signed-test-token"
    assert response.json()["token_type"] == "bearer"


def test_login_rejects_invalid_credentials() -> None:
    class RejectingUserService:
        async def authenticate(self, *, email: str, password: str):
            raise InvalidCredentialsError("Invalid email or password")

    app.dependency_overrides[get_user_service] = lambda: RejectingUserService()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "agent@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_reports_invalid_json_body() -> None:
    response = client.post(
        "/api/v1/auth/login",
        data="{'email':'admin@example.com','password':'ADMIN12345'}",
        headers={"Content-Type": "application/json"},
    )

    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "invalid_request"
    assert body["message"] == "Invalid JSON body. Check quotes, commas and braces."
    assert body["details"][0]["field"] == "body"
    assert body["details"][0]["type"] == "json_invalid"


def test_login_reports_missing_field() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com"},
    )

    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "invalid_request"
    assert body["message"] == "Invalid field 'password': Field required"
    assert body["details"][0]["field"] == "password"
