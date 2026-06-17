from typing import Any

from pydantic import BaseModel, Field


class GroupTaskCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    device_ids: list[int] = Field(..., min_length=1)
    fio_config: dict[str, Any] = Field(...)
    device_path: str | None = Field(default=None, max_length=255)
    device_paths: dict[str, str] | None = Field(default=None)
