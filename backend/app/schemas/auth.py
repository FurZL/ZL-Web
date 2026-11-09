"""认证 / 用户相关 Schema。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=64)
    email: EmailStr
    phone: str = Field(description="含国家/地区码，将标准化为 E.164")
    password: str = Field(min_length=8, max_length=128)
    email_code: str
    phone_code: str
    applied_role: str | None = Field(default=None, description="申请角色，例如 photographer")
    application_reason: str | None = None
    application_portfolio: str | None = None


class LoginRequest(BaseModel):
    account: str = Field(description="用户名/邮箱/手机号")
    password: str


class OtpRequest(BaseModel):
    target: str = Field(description="邮箱或手机号")
    purpose: str = "register"


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


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    email: EmailStr
    role: str
    status: str
    applied_role: str | None
    application_reason: str | None
    application_portfolio: str | None
    created_at: datetime