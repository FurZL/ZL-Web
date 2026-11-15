"""认证 / 用户相关 Schema。"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    email: str = Field(default="")
    phone: str = Field(default="")
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(default="")
    email_code: str = Field(default="")
    phone_code: str = Field(default="")
    applied_role: str | None = Field(default=None, description="申请角色，例如 photographer")
    application_reason: str | None = None
    application_portfolio: str | None = None

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v) or not re.search(r"[a-z]", v) or not re.search(r"[0-9]", v):
            raise ValueError("密码必须包含大写字母、小写字母和数字")
        return v


class LoginRequest(BaseModel):
    account: str = Field(description="用户名/邮箱/手机号")
    password: str
    verification_token: str | None = Field(default=None, description="人机验证 token")


class OtpRequest(BaseModel):
    target: str = Field(description="邮箱或手机号")
    purpose: str = "register"
    verification_token: str | None = Field(default=None, description="人机验证 token")


class VerifyOtpRequest(BaseModel):
    target: str
    purpose: str
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordForgotRequest(BaseModel):
    target: str


class PasswordResetRequest(BaseModel):
    target: str
    code: str
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirm: str = Field(default="")

    @field_validator("new_password")
    @classmethod
    def _validate_new_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v) or not re.search(r"[a-z]", v) or not re.search(r"[0-9]", v):
            raise ValueError("密码必须包含大写字母、小写字母和数字")
        return v


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    email: str = Field(default="")
    role: str
    status: str
    applied_role: str | None
    application_reason: str | None
    application_portfolio: str | None
    created_at: datetime