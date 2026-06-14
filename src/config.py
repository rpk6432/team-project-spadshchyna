from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str

    # JWT
    jwt_secret: str
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 7

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # S3 / MinIO
    s3_endpoint_url: str = "http://minio:9000"
    s3_public_url: str = "http://localhost:9000"
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "spadshchyna"

    # Email
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_from: str = "noreply@spadshchyna.ua"

    # Pricing
    service_fee_pct: int = 3


settings = Settings()
