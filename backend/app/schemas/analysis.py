from pydantic import BaseModel


class AiAnalysisRequest(BaseModel):
    include_fio: bool = True
    include_host_monitor: bool = True
    include_disk_monitor: bool = True
