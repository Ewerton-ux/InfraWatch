from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models.entities import User, Server, MetricLog, Alert
from app.core.security import get_password_hash
from app.api import auth, monitoring
import random
from datetime import datetime, timedelta

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Plataforma de Observabilidade e Monitoramento de Infraestrutura"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics Instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Rotas
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(monitoring.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def startup_event():
    # Cria tabelas
    Base.metadata.create_all(bind=engine)
    
    # Seed inicial
    db = SessionLocal()
    try:
        # Cria admin default se não existir
        admin = db.query(User).filter(User.email == "admin@infrawatch.io").first()
        if not admin:
            admin = User(
                email="admin@infrawatch.io",
                full_name="InfraWatch Admin",
                hashed_password=get_password_hash("admin123"),
                role="admin"
            )
            db.add(admin)
            db.commit()

        # Cria servidores de exemplo se banco estiver vazio
        if db.query(Server).count() == 0:
            servers = [
                Server(name="prod-k8s-master-01", hostname="k8s-m1.prod.local", ip_address="192.168.10.10", environment="production", status="ONLINE"),
                Server(name="prod-k8s-worker-01", hostname="k8s-w1.prod.local", ip_address="192.168.10.11", environment="production", status="ONLINE"),
                Server(name="prod-db-postgres-01", hostname="pg-primary.prod.local", ip_address="192.168.10.20", environment="production", status="WARNING"),
                Server(name="staging-api-gateway", hostname="gw-stg.internal", ip_address="192.168.20.15", environment="staging", status="ONLINE"),
                Server(name="redis-cache-cluster", hostname="redis-01.prod.local", ip_address="192.168.10.30", environment="production", status="ONLINE")
            ]
            db.add_all(servers)
            db.commit()

            # Popula com métricas históricas recentes para visualização inicial
            now = datetime.utcnow()
            for s in servers:
                base_cpu = 30.0 if s.status == "ONLINE" else 82.0
                base_mem = 45.0 if s.status == "ONLINE" else 88.0
                for i in range(20):
                    m = MetricLog(
                        server_id=s.id,
                        cpu_percent=round(max(5.0, min(99.0, base_cpu + random.uniform(-10, 15))), 1),
                        memory_percent=round(max(10.0, min(98.0, base_mem + random.uniform(-5, 8))), 1),
                        disk_percent=62.5,
                        network_latency_ms=round(random.uniform(1.2, 12.5), 2),
                        timestamp=now - timedelta(minutes=(20 - i) * 2)
                    )
                    db.add(m)

            # Alerta de exemplo
            db.add(Alert(
                server_id=servers[2].id,
                severity="WARNING",
                message="Alto consumo de memória detectado em prod-db-postgres-01 (> 85%)",
                resolved=False
            ))
            db.commit()
    finally:
        db.close()

@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "metrics": "/metrics"
    }
