from typing import Any

from pydantic import BaseModel, Field


class RegressionRunRequest(BaseModel):
    task_id: int = Field(..., gt=0)
    baseline_id: int = Field(..., gt=0)
