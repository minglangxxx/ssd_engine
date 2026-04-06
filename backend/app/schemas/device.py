from pydantic import BaseModel, Field


class DeviceAddRequest(BaseModel):
    ip: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    agent_port: int = Field(default=8080, ge=1, le=65535)


class DeviceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    agent_port: int | None = Field(default=None, ge=1, le=65535)


class DeviceTestConnectionRequest(BaseModel):
    ip: str = Field(..., min_length=1, max_length=50)
    user: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=255)
    agent_port: int = Field(default=8080, ge=1, le=65535)
