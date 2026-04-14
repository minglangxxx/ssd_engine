from pydantic import BaseModel, Field


class AiAnalysisRequest(BaseModel):
    include_fio: bool = True
    include_host_monitor: bool = True
    include_disk_monitor: bool = True
    window_before_seconds: int = Field(default=30, ge=0, le=3600)
    window_after_seconds: int = Field(default=30, ge=0, le=3600)
