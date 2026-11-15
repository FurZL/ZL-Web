"""阿里云短信服务 Provider。"""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.config import settings
from app.providers.sms.base import SmsProvider

logger = logging.getLogger(__name__)


class AliyunSmsProvider(SmsProvider):
    def __init__(self) -> None:
        self.access_key_id = settings.sms_aliyun_access_key_id
        self.access_key_secret = settings.sms_aliyun_access_key_secret
        self.sign_name = settings.sms_aliyun_sign_name
        self.template_code = settings.sms_aliyun_template_code
        self.region = settings.sms_aliyun_region

    @property
    def configured(self) -> bool:
        return bool(self.access_key_id and self.access_key_secret and self.sign_name and self.template_code)

    async def send_code(self, phone: str, template: str, variables: dict) -> str:
        """发送短信验证码，返回阿里云 BizId。"""
        if not self.configured:
            raise RuntimeError("阿里云短信未配置")

        from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
        from alibabacloud_tea_openapi import models as open_api_models

        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            region_id=self.region,
        )
        client = DysmsapiClient(config)

        code = variables.get("code", "")
        request = dysmsapi_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=self.sign_name,
            template_code=self.template_code,
            template_param=json.dumps({"code": code}, ensure_ascii=False),
        )

        try:
            response = await asyncio.to_thread(client.send_sms, request)
        except Exception as exc:
            logger.warning("阿里云短信发送失败 phone=%s err=%s", phone, exc)
            raise RuntimeError("短信发送失败，请稍后重试") from exc

        if response.body.code != "OK":
            logger.warning(
                "阿里云短信 API 返回错误 phone=%s code=%s message=%s",
                phone, response.body.code, response.body.message,
            )
            raise RuntimeError("短信发送失败，请稍后重试")

        logger.info("阿里云短信发送成功 phone=%s biz_id=%s", phone, response.body.biz_id)
        return response.body.biz_id or "sent"
