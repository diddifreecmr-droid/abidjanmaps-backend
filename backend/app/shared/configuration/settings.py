from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AbidjanMaps Routing Service"
    app_version: str = "1.0.0"
    osrm_base_url: str = "http://osrm.alphamotors-cameroun.fyi"
    osrm_username: str | None = None
    osrm_password: str | None = None
    osrm_profile: str = "driving"
    osrm_timeout_seconds: int = 5
    enrichment_match_tolerance_m: float = 15.0
    database_url: str = "postgresql+asyncpg://mapuser:mapdevpassword@db:5432/mapdb"
    auth_secret_key: str = "dev-only-change-this-secret-before-deployment"
    auth_token_expire_minutes: int = 480
    auth_algorithm: str = "HS256"
    coverage_min_lat: float = 5.0
    coverage_max_lat: float = 6.0
    coverage_min_lng: float = -5.0
    coverage_max_lng: float = -3.0
    base_fare_xof: int = 500
    price_per_km_xof: int = 200
    price_per_minute_xof: int = 20
    minimum_fare_xof: int = 1000
    fare_rounding_xof: int = 50
    allowed_profile: str = "car"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
