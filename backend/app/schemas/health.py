from typing import Dict, Any, Optional
from pydantic import BaseModel

class ServiceHealthStatus(BaseModel):
    status: str # "healthy" | "degraded" | "unhealthy"
    latency_ms: Optional[float] = None
    details: Optional[str] = None

class HealthStatusResponse(BaseModel):
    status: str # "healthy" | "degraded" | "unhealthy"
    environment: str
    version: str = "1.0.0"
    services: Dict[str, ServiceHealthStatus]
