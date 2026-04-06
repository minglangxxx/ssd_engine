from typing import Any, Literal

from pydantic import BaseModel, Field


class FioConfigSchema(BaseModel):
    rw: Literal['read', 'write', 'rw', 'randread', 'randwrite', 'randrw'] = 'randread'
    bs: str | None = Field(default=None, pattern=r'^\d+[KMGkmg]$')
    size: str | None = Field(default=None, pattern=r'^\d+[KMGkmg]$')
    numjobs: int | None = Field(default=None, ge=1, le=128)
    iodepth: int | None = Field(default=None, ge=1, le=256)
    runtime: int | None = Field(default=None, ge=1, le=86400)
    time_based: bool | None = True
    ioengine: str | None = None
    direct: bool | None = None
    sync: bool | None = None
    fsync: int | None = Field(default=None, ge=0)
    buffer_pattern: str | None = None
    random_distribution: str | None = None
    randseed: int | None = None
    rwmixread: int | None = Field(default=None, ge=0, le=100)
    rwmixwrite: int | None = Field(default=None, ge=0, le=100)
    thinktime: int | None = Field(default=None, ge=0)
    latency_target: int | None = Field(default=None, ge=0)
    rate: int | None = Field(default=None, ge=0)
    rate_iops: int | None = Field(default=None, ge=0)
    verify: str | None = None
    verify_fatal: bool | None = None
    cpus_allowed: str | None = None
    mem: str | None = None
    stats_interval: int | None = Field(default=None, ge=100, le=60000)
    log_avg_msec: int | None = Field(default=None, ge=100, le=60000)
    loops: int | None = Field(default=None, ge=1, le=10000)
    startdelay: int | None = Field(default=None, ge=0, le=3600)


class TaskCreateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    device_ip: str = Field(..., min_length=1, max_length=50)
    device_user: str = Field(..., min_length=1, max_length=64)
    device_password: str = Field(..., min_length=1, max_length=255)
    device_path: str = Field(..., min_length=1, max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)
    fault_type: Literal['none', 'power_off', 'drop_device'] = 'none'
