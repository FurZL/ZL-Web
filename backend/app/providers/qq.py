"""QQ 互联 OAuth Provider。"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings

QQ_AUTHORIZE_URL = "https://graph.qq.com/oauth2.0/authorize"
QQ_TOKEN_URL = "https://graph.qq.com/oauth2.0/token"
QQ_OPENID_URL = "https://graph.qq.com/oauth2.0/me"
QQ_USER_INFO_URL = "https://graph.qq.com/user/get_user_info"


class QqOAuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class QqOAuthProvider:
    @property
    def configured(self) -> bool:
        return bool(settings.qq_app_id and settings.qq_app_key)

    def build_authorize_url(self, state: str) -> str:
        if not self.configured:
            raise QqOAuthError(
                "OAUTH_QQ_UNAVAILABLE",
                "QQ 登录暂未配置",
                status_code=503,
            )
        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.qq_app_id,
                "redirect_uri": settings.qq_redirect_uri,
                "state": state,
                "scope": "get_user_info",
            }
        )
        return f"{QQ_AUTHORIZE_URL}?{query}"

    async def exchange_code(self, code: str) -> dict:
        if not self.configured:
            raise QqOAuthError(
                "OAUTH_QQ_UNAVAILABLE",
                "QQ 登录暂未配置",
                status_code=503,
            )

        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.get(
                QQ_TOKEN_URL,
                params={
                    "grant_type": "authorization_code",
                    "client_id": settings.qq_app_id,
                    "client_secret": settings.qq_app_key,
                    "code": code,
                    "redirect_uri": settings.qq_redirect_uri,
                    "fmt": "json",
                },
            )
            token_data = token_resp.json()
            if "error" in token_data:
                description = token_data.get("error_description") or "授权码无效"
                raise QqOAuthError(
                    f"QQ_{token_data['error']}",
                    description,
                    status_code=401,
                )
            access_token = token_data.get("access_token")
            if not access_token:
                raise QqOAuthError("QQ_TOKEN_FAILED", "获取 QQ 令牌失败")

            openid_resp = await client.get(
                QQ_OPENID_URL,
                params={"access_token": access_token, "fmt": "json"},
            )
            openid_data = openid_resp.json()
            provider_user_id = openid_data.get("openid")
            if not provider_user_id:
                raise QqOAuthError("QQ_OPENID_FAILED", "获取 QQ 身份标识失败")

            user_resp = await client.get(
                QQ_USER_INFO_URL,
                params={
                    "access_token": access_token,
                    "oauth_consumer_key": settings.qq_app_id,
                    "openid": provider_user_id,
                },
            )
            user_data = user_resp.json()

        return {
            "provider_user_id": provider_user_id,
            "unionid": openid_data.get("unionid"),
            "nickname": user_data.get("nickname") or "QQ用户",
            "avatar_url": (
                user_data.get("figureurl_qq_2")
                or user_data.get("figureurl_qq_1")
                or None
            ),
            "access_token": access_token,
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "raw_profile": user_data,
        }

