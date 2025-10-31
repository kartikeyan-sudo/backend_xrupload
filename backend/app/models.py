from pydantic import BaseModel, Field
from typing import Optional

class UploadResponse(BaseModel):
    job_id: str
    filename: str
    message: str = "accepted"

class StatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = Field(0, ge=0, le=100)
    message: Optional[str] = None
    result_url: Optional[str] = None
    error: Optional[str] = None