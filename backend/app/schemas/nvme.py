from pydantic import BaseModel, Field


class SmartHistoryQuery(BaseModel):
    disk_name: str = Field(..., min_length=1, description='NVMe 磁盘名称')
    start: str | None = Field(None, description='起始时间 ISO 格式')
    end: str | None = Field(None, description='结束时间 ISO 格式')


class RunValidationRequest(BaseModel):
    disk_name: str = Field(..., min_length=1, description='NVMe 磁盘名称')
    test_type: str = Field(..., pattern=r'^(identify|namespace|smart|error_log|feature|fw_slot)$',
                           description='校验类型')