from typing import Any

from pydantic import BaseModel, Field


class BaselineCreateRequest(BaseModel):
    task_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=128)
    device_model: str | None = Field(default=None, max_length=128)
    firmware: str | None = Field(default=None, max_length=64)
