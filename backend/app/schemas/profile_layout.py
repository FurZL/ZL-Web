"""个人空间布局端点请求 Schema。"""

from pydantic import BaseModel, ConfigDict, StrictBool


class ProfileImageDisplayPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    is_displayable: StrictBool
