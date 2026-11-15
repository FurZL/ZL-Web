"""SMTP 邮件 Provider（支持 SSL/TLS）。

发件人名称使用 settings.app_name（对应 .env 的 APP_NAME）。
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)

_HTML_WRAPPER = """\
<div style="border-radius:10px;font-size:13px;color:#555;width:666px;\
font-family:'Century Gothic','Trebuchet MS','Hiragino Sans GB',\
'Microsoft Yahei',Tahoma,Helvetica,Arial,SimSun,sans-serif;\
margin:50px auto;border:1px solid #eee;max-width:100%;\
background:#fff;box-shadow:0 1px 5px rgba(0,0,0,.15)">
  <div style="width:100%;background:linear-gradient(90deg,#6B5CE7,#F0A6C8);\
color:#fff;border-radius:10px 10px 0 0;height:66px">
    <p style="font-size:15px;word-break:break-all;padding:23px 32px;margin:0;\
background-color:hsla(0,0%,100%,.4);border-radius:10px 10px 0 0">
      {header_title}
    </p>
  </div>
  <div style="margin:40px auto;width:90%">
    {body_html}
    <p style="margin:20px 0 0 0;font-size:12px;color:#aaa;\
border-top:1px solid #eee;padding-top:16px">
      此邮件由 {site_name} 自动发送，请勿直接回复。
    </p>
  </div>
</div>"""


def _build_html(subject: str, body_lines: list[str], site_name: str) -> str:
    parts = []
    for line in body_lines:
        parts.append(f'<p style="margin:20px 0;font-size:14px;color:#555">{line}</p>')
    return _HTML_WRAPPER.format(
        header_title=subject,
        body_html="\n".join(parts),
        site_name=site_name,
    )


_OTP_BODY = [
    '您的验证码是：<strong style="font-size:18px;color:#6B5CE7">{code}</strong>',
    "该验证码 {ttl_minutes} 分钟内有效，请勿透露给他人。",
    "如果您没有请求此验证码，请忽略这封邮件。",
]

_REGISTER_PENDING_BODY = [
    "感谢您注册 {site_name}！",
    "您的账号 <strong>{username}</strong> 已提交成功，目前正在等待管理员审批。",
    "审批通过后您将收到邮件通知，届时即可登录使用。",
    "如有疑问，请联系管理员。",
]

_ACCOUNT_APPROVED_BODY = [
    "恭喜！您在 {site_name} 的账号 <strong>{username}</strong> 已通过审批。",
    "现在您可以登录并开始使用所有功能了。",
]

_ACCOUNT_REJECTED_BODY = [
    "很遗憾，您在 {site_name} 的注册申请未被通过。",
    "如有疑问，请联系管理员了解详情。",
]

_TEST_BODY = [
    "这封邮件来自 {site_name} 的 SMTP 配置测试。",
    "如果您收到了这封邮件，说明邮件发送功能已正常运作。",
]


class SmtpEmailProvider:
    def __init__(self) -> None:
        self.host: str = settings.smtp_host or ""
        self.port: int = settings.smtp_port
        self.user: str = settings.smtp_user or ""
        self.password: str = settings.smtp_password or ""
        self.from_addr: str = settings.smtp_from or self.user
        self.from_name: str = settings.app_name
        self.use_ssl: bool = settings.smtp_use_ssl

    @property
    def configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    async def send(
        self,
        to: str,
        subject: str,
        template: str,
        variables: dict | None = None,
    ) -> str:
        if not self.configured:
            raise RuntimeError("SMTP 未配置")

        vars_dict = variables or {}

        if template == "otp":
            code = vars_dict.get("code", "000000")
            ttl = vars_dict.get("ttl_minutes", 10)
            body_lines = [line.format(code=code, ttl_minutes=ttl) for line in _OTP_BODY]
        elif template == "register_pending":
            body_lines = [line.format(site_name=self.from_name, username=vars_dict.get("username", "")) for line in _REGISTER_PENDING_BODY]
        elif template == "account_approved":
            body_lines = [line.format(site_name=self.from_name, username=vars_dict.get("username", "")) for line in _ACCOUNT_APPROVED_BODY]
        elif template == "account_rejected":
            body_lines = [line.format(site_name=self.from_name, username=vars_dict.get("username", "")) for line in _ACCOUNT_REJECTED_BODY]
        elif template == "test":
            body_lines = [line.format(site_name=self.from_name) for line in _TEST_BODY]
        else:
            body_lines = [template]

        html = _build_html(subject, body_lines, self.from_name)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_addr}>"
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))

        def _do() -> None:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=15)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=15)
                server.starttls()
            try:
                server.login(self.user, self.password)
                server.sendmail(self.from_addr, [to], msg.as_string())
            finally:
                server.quit()

        try:
            await asyncio.to_thread(_do)
        except Exception as exc:
            logger.warning("SMTP 发送失败 to=%s: %s", to, exc, exc_info=True)
            raise RuntimeError("邮件发送失败") from exc

        logger.info("SMTP sent to=%s subject=%s", to, subject)
        return "ok"