"""第三方登录端点：发起授权、回调解析、账号绑定。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.response import error_to_http, ok
from app.api.v1.endpoints.captcha import check_verification_token
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.providers.qq import QqOAuthError
from app.services import site_setting
from app.services import third_party_auth as oauth_service

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


class OauthStartRequest(BaseModel):
    verification_token: str | None = None
    return_to: str | None = Field(default=None, max_length=256)


class OauthBindRequest(BaseModel):
    oauth_token: str
    account: str
    password: str
    verification_token: str | None = None


def _validate_return_to(value: str | None) -> str | None:
    if not value:
        return None
    if not value.startswith("/") or value.startswith("//"):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_RETURN_TO", "message": "返回地址无效"},
        )
    return value


@router.get("/providers")
async def providers_public(db: AsyncSession = Depends(get_db)):
    cfg = await site_setting.get_oauth_config(db)
    return ok(
        {
            "providers": [
                {
                    "id": "qq",
                    "enabled": bool(cfg.get("enabled") and cfg.get("qq_enabled")),
                }
            ],
            "frontend_base_url": settings.oauth_frontend_base_url,
        }
    )


@router.post("/{provider}/start")
async def oauth_start(
    provider: str,
    body: OauthStartRequest,
    db: AsyncSession = Depends(get_db),
):
    if not await check_verification_token(body.verification_token or ""):
        raise HTTPException(
            status_code=400,
            detail={"code": "CAPTCHA_REQUIRED", "message": "请先完成人机验证"},
        )
    if not await oauth_service.is_oauth_public_enabled(db, provider):
        raise HTTPException(
            status_code=503,
            detail={"code": "OAUTH_DISABLED", "message": "该第三方登录方式未开启"},
        )

    _ = _validate_return_to(body.return_to)
    # 公共回调卡片读取/绑定口令需要 return_to，这里拼进 state 由前端在回调页读取。
    authorize_url = await oauth_service.build_authorize_url(
        provider,
        mode="login",
        user=None,
        return_to=_validate_return_to(body.return_to),
    )
    return ok({"authorize_url": authorize_url})


@router.post("/{provider}/bind-start")
async def oauth_bind_start(
    provider: str,
    body: OauthStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await check_verification_token(body.verification_token or ""):
        raise HTTPException(
            status_code=400,
            detail={"code": "CAPTCHA_REQUIRED", "message": "请先完成人机验证"},
        )
    if not await oauth_service.is_oauth_public_enabled(db, provider):
        raise HTTPException(
            status_code=503,
            detail={"code": "OAUTH_DISABLED", "message": "该第三方登录方式未开启"},
        )
    _ = _validate_return_to(body.return_to)
    authorize_url = await oauth_service.build_authorize_url(
        provider,
        mode="bind",
        user=user,
        return_to=_validate_return_to(body.return_to),
    )
    return ok({"authorize_url": authorize_url})


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    if provider != "qq":
        raise HTTPException(
            status_code=400,
            detail={"code": "OAUTH_PROVIDER_UNSUPPORTED", "message": "暂不支持该登录方式"},
        )
    try:
        result = await oauth_service.exchange_and_resolve(
            db,
            provider=provider,
            code=code,
            state=state,
        )
    except QqOAuthError as exc:
        raise error_to_http(exc)
    if result.get("refresh_token"):
        response.set_cookie(
            value=result["refresh_token"],
            key=settings.auth_cookie_name,
            max_age=settings.refresh_token_ttl_days * 24 * 3600,
            path=f"{settings.api_v1_prefix}/auth",
            httponly=True,
            secure=settings.auth_cookie_secure or settings.is_production,
            samesite=settings.auth_cookie_samesite,
        )
    return ok(result)


@router.post("/{provider}/bind")
async def oauth_bind(
    provider: str,
    body: OauthBindRequest,
    db: AsyncSession = Depends(get_db),
):
    if provider != "qq":
        raise HTTPException(
            status_code=400,
            detail={"code": "OAUTH_PROVIDER_UNSUPPORTED", "message": "暂不支持该登录方式"},
        )
    if not await check_verification_token(body.verification_token or ""):
        raise HTTPException(
            status_code=400,
            detail={"code": "CAPTCHA_REQUIRED", "message": "请先完成人机验证"},
        )
    try:
        result = await oauth_service.bind_with_credentials(
            db,
            oauth_token=body.oauth_token,
            account=body.account,
            password=body.password,
        )
    except QqOAuthError as exc:
        raise error_to_http(exc)
    return ok(result)

