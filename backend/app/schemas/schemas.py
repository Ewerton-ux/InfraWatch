from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# Token
class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenPayload(BaseModel):
    sub: Optional[str] = None

# User
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[str] = "operator"
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# Server
class ServerBase(BaseModel):
    name: str
    hostname: str
    ip_address: str
    environment: Optional[str] = "production"

class ServerCreate(ServerBase):
    pass

class ServerResponse(ServerBase):
    id: int
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

# Metrics
class MetricCreate(BaseModel):
    server_id: int
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_latency_ms: Optional[float] = 0.0

class MetricResponse(MetricCreate):
    id: int
    timestamp: datetime
    class Config:
        from_attributes = True

# Alerts
class AlertBase(BaseModel):
    server_id: Optional[int] = None
    severity: str
    message: str

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Dashboard Overview
class DashboardOverview(BaseModel):
    total_servers: int
    healthy_servers: int
    warning_servers: int
    critical_servers: int
    total_active_alerts: int
    average_cpu: float
    average_memory: float
