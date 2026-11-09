"""Provider 抽象层。

所有外部服务通过 Provider/Adapter 接口接入，避免在业务路由中写死云厂商 SDK。
具体实现在 `app/providers/` 下对应子目录。
"""

from app.providers.storage.base import StorageProvider  # noqa: F401
from app.providers.email.base import EmailProvider  # noqa: F401
from app.providers.sms.base import SmsProvider  # noqa: F401
from app.providers.captcha.base import CaptchaProvider  # noqa: F401
from app.providers.human_verification.base import HumanVerificationProvider  # noqa: F401