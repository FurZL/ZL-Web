"""个人空间布局端点请求 Schema。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class ProfileImageDisplayPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    is_displayable: StrictBool


class ProfileTheme(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    primary: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    accent: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    background_type: Literal["solid", "gradient", "image"]
    background_key: str | None = Field(min_length=1, max_length=1024)
    background_blur: int = Field(ge=0, le=20)
    card_style: Literal["glass", "solid", "outline"]
