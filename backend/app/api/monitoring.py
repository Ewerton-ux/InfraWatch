from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import random

from app.core.database import get_db
from app.models.entities import Server, MetricLog, Alert, User
from app.schemas.schemas import (
    ServerCreate, ServerResponse, MetricCreate, MetricResponse,
    AlertCreate, AlertResponse, DashboardOverview
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/monitoring", tags=["Monitoramento e Infraestrutura"])

# --- SERVIDORES ---
@router.get("/servers", response_model=List[ServerResponse])
def get_servers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Server).all()

@router.post("/servers", response_model=ServerResponse)
def create_server(server_in: ServerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    server = Server(
        name=server_in.name,
        hostname=server_in.hostname,
        ip_address=server_in.ip_address,
        environment=server_in.environment,
        status="ONLINE"
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server

@router.delete("/servers/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    db.delete(server)
    db.commit()
    return {"message": "Servidor removido com sucesso"}

# --- MÉTRICAS ---
@router.post("/metrics", response_model=MetricResponse)
def push_metric(metric_in: MetricCreate, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == metric_in.server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    
    metric = MetricLog(
        server_id=metric_in.server_id,
        cpu_percent=metric_in.cpu_percent,
        memory_percent=metric_in.memory_percent,
        disk_percent=metric_in.disk_percent,
        network_latency_ms=metric_in.network_latency_ms
    )
    db.add(metric)
    
    # Atualiza status do servidor de acordo com limites operacionais
    if metric_in.cpu_percent > 90 or metric_in.memory_percent > 90:
        server.status = "CRITICAL"
        # Cria alerta automático
        alert = Alert(
            server_id=server.id,
            severity="CRITICAL",
            message=f"Consumo crítico no servidor {server.name}: CPU {metric_in.cpu_percent}%, Memória {metric_in.memory_percent}%"
        )
        db.add(alert)
    elif metric_in.cpu_percent > 75 or metric_in.memory_percent > 80:
        server.status = "WARNING"
    else:
        server.status = "ONLINE"

    db.commit()
    db.refresh(metric)
    return metric

@router.get("/metrics/server/{server_id}", response_model=List[MetricResponse])
def get_server_metrics(
    server_id: int, 
    limit: int = Query(default=50, ge=1, le=500), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    metrics = db.query(MetricLog).filter(MetricLog.server_id == server_id)\
                .order_by(MetricLog.timestamp.desc())\
                .limit(limit).all()
    return list(reversed(metrics))

@router.post("/simulate-tick")
def simulate_tick(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    servers = db.query(Server).all()
    for s in servers:
        base_cpu = 30.0 if s.status == "ONLINE" else 80.0
        base_mem = 40.0 if s.status == "ONLINE" else 85.0
        cpu = round(max(5.0, min(99.0, base_cpu + random.uniform(-10, 15))), 1)
        mem = round(max(10.0, min(98.0, base_mem + random.uniform(-5, 8))), 1)
        db.add(MetricLog(
            server_id=s.id,
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=60.0,
            network_latency_ms=round(random.uniform(1.2, 12.5), 2)
        ))
    db.commit()
    return {"tick": True, "servers": len(servers)}

# --- ALERTAS ---
@router.post("/alerts", response_model=AlertResponse)
def create_alert(alert_in: AlertCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if alert_in.server_id is not None:
        server = db.query(Server).filter(Server.id == alert_in.server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Servidor não encontrado")
    alert = Alert(
        server_id=alert_in.server_id,
        severity=alert_in.severity,
        message=alert_in.message,
        resolved=False
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(resolved: Optional[bool] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Alert)
    if resolved is not None:
        query = query.filter(Alert.resolved == resolved)
    return query.order_by(Alert.created_at.desc()).limit(100).all()

@router.put("/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert

# --- DASHBOARD STATS ---
@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    servers = db.query(Server).all()
    total_servers = len(servers)
    healthy = sum(1 for s in servers if s.status == "ONLINE")
    warning = sum(1 for s in servers if s.status == "WARNING")
    critical = sum(1 for s in servers if s.status == "CRITICAL")
    
    active_alerts = db.query(Alert).filter(Alert.resolved == False).count()

    # Média recente de CPU e Memória (últimos 15 min)
    since = datetime.utcnow() - timedelta(minutes=15)
    recent_metrics = db.query(
        func.avg(MetricLog.cpu_percent).label("avg_cpu"),
        func.avg(MetricLog.memory_percent).label("avg_mem")
    ).filter(MetricLog.timestamp >= since).first()

    avg_cpu = round(float(recent_metrics.avg_cpu or 0.0), 2)
    avg_mem = round(float(recent_metrics.avg_mem or 0.0), 2)

    return DashboardOverview(
        total_servers=total_servers,
        healthy_servers=healthy,
        warning_servers=warning,
        critical_servers=critical,
        total_active_alerts=active_alerts,
        average_cpu=avg_cpu,
        average_memory=avg_mem
    )
