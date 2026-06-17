from typing import Any

from pydantic import BaseModel, Field


class SniaTaskCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    device_id: int = Field(..., gt=0)
    device_path: str = Field(..., min_length=1, max_length=255)
    config: dict[str, Any] | None = Field(default=None)
