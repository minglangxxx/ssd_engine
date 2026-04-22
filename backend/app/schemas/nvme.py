from pydantic import BaseModel, Field


class SmartHistoryQuery(BaseModel):
    disk_name: str = Field(..., min_length=1, description='NVMe 磁盘名称')
    start: str | None = Field(None, description='起始时间 ISO 格式')
    end: str | None = Field(None, description='结束时间 ISO 格式')