from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="operator")  # admin, operator, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    environment = Column(String, default="production")  # production, staging, dev
    status = Column(String, default="ONLINE")  # ONLINE, WARNING, CRITICAL, OFFLINE
    created_at = Column(DateTime, default=datetime.utcnow)
    
    metrics = relationship("MetricLog", back_populates="server", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="server", cascade="all, delete-orphan")

class MetricLog(Base):
    __tablename__ = "metric_logs"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_percent = Column(Float, nullable=False)
    network_latency_ms = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    server = relationship("Server", back_populates="metrics")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    severity = Column(String, default="WARNING")  # INFO, WARNING, CRITICAL
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    server = relationship("Server", back_populates="alerts")
