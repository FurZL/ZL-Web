"""应用配置。

所有配置从环境变量读取，通过 pydantic-settings 校验。
敏感密钥不进 Git，生产由 systemd 的 EnvironmentFile 注入。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 基础
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Furry ZJUT", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="replace-me", alias="SECRET_KEY")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # 数据库
    database_url: str = Field(
        default="postgresql+psycopg://furry_app:furry_dev_password@localhost:5432/furry_zjut",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=2, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # 前端与 CORS
    frontend_origins: str = Field(
        default="http://localhost:5173", alias="FRONTEND_ORIGINS"
    )

    # 对象存储（本地测试与生产均使用腾讯云 COS；单桶，公开/私有靠前缀隔离）
    storage_provider: str = Field(default="cos", alias="STORAGE_PROVIDER")
    cos_secret_id: str | None = Field(default=None, alias="COS_SECRET_ID")
    cos_secret_key: str | None = Field(default=None, alias="COS_SECRET_KEY")
    cos_region: str | None = Field(default=None, alias="COS_REGION")
    cos_bucket: str | None = Field(default=None, alias="COS_BUCKET")
    public_asset_base_url: str = Field(
        default="https://img.example.com", alias="PUBLIC_ASSET_BASE_URL"
    )
    private_url_ttl_seconds: int = Field(default=900, alias="PRIVATE_URL_TTL_SECONDS")
    profile_layout_max_blocks: int = Field(default=16, alias="PROFILE_LAYOUT_MAX_BLOCKS")

    # 邮件 / 短信 / 人机验证
    email_provider: str | None = Field(default=None, alias="EMAIL_PROVIDER")
    email_api_key: str | None = Field(default=None, alias="EMAIL_API_KEY")
    email_from: str | None = Field(default=None, alias="EMAIL_FROM")
    sms_provider: str | None = Field(default=None, alias="SMS_PROVIDER")
    sms_api_key: str | None = Field(default=None, alias="SMS_API_KEY")
    captcha_provider: str | None = Field(default=None, alias="CAPTCHA_PROVIDER")
    captcha_secret_key: str | None = Field(default=None, alias="CAPTCHA_SECRET_KEY")
    human_verification_provider: str | None = Field(
        default=None, alias="HUMAN_VERIFICATION_PROVIDER"
    )
    human_verification_secret_key: str | None = Field(
        default=None, alias="HUMAN_VERIFICATION_SECRET_KEY"
    )

    # 认证
    access_token_ttl_minutes: int = Field(default=15, alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=14, alias="REFRESH_TOKEN_TTL_DAYS")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    password_hash_scheme: str = Field(default="argon2", alias="PASSWORD_HASH_SCHEME")

    # 验证码（OTP）
    otp_ttl_seconds: int = Field(default=600, alias="OTP_TTL_SECONDS")
    otp_max_attempts: int = Field(default=5, alias="OTP_MAX_ATTEMPTS")
    # 开发模式：不真正发送邮件/短信，验证码返回在响应里（仅用于本地联调）
    otp_dev_mode: bool = Field(default=False, alias="OTP_DEV_MODE")

    # 上传
    upload_max_bytes: int = Field(default=52_428_800, alias="UPLOAD_MAX_BYTES")

    # 图片处理（后台任务）
    image_display_max_px: int = Field(default=2000, alias="IMAGE_DISPLAY_MAX_PX")
    image_thumb_max_px: int = Field(default=800, alias="IMAGE_THUMB_MAX_PX")
    image_quality: int = Field(default=85, alias="IMAGE_QUALITY")
    image_max_pixels: int = Field(
        default=40_000_000, alias="IMAGE_MAX_PIXELS"
    )  # 防解压炸弹（约 40MP）
    image_worker_concurrency: int = Field(default=2, alias="IMAGE_WORKER_CONCURRENCY")

    # 可观测性
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | list[str]) -> list[str] | str:
        # 也支持逗号分隔字符串；后续统一走 cors_origins 属性
        return value

    @property
    def cors_origins(self) -> list[str]:
        if isinstance(self.frontend_origins, list):
            return self.frontend_origins
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
