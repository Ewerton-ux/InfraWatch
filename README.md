<div align="center">

# 🔭 InfraWatch

**Plataforma de Observabilidade & Monitoramento de Infraestrutura**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)

> Plataforma unificada de observabilidade para centralizar **métricas**, **logs** e **alertas** em um único painel operacional — desenvolvida como laboratório de aprendizado em Cloud, DevOps e Infraestrutura Moderna.

[📊 Dashboard](#-como-executar) · [📡 API Docs](#-endpoints-da-api) · [🐳 Docker](#-execução-com-docker-compose) · [🛠️ Tecnologias](#️-tecnologias-utilizadas)

</div>

---

## 📍 Situação

Durante estudos em **Cloud Computing**, **DevOps** e **Infraestrutura**, identifiquei a necessidade de uma solução centralizada para monitoramento de servidores, containers e aplicações — proporcionando maior visibilidade operacional e tomada de decisão baseada em métricas em tempo real.

## 🎯 Objetivo

Projetar e desenvolver uma plataforma de observabilidade capaz de consolidar métricas, logs e alertas em um único ambiente, proporcionando monitoramento eficiente, escalável e seguro para equipes de infraestrutura e operações.

---

## ✨ Funcionalidades

- 📡 **Dashboard em Tempo Real** — visualização de CPU, memória e disco com gráficos interativos atualizados automaticamente a cada 6 segundos
- 🖥️ **Gerenciamento de Nós** — cadastro, listagem e status de servidores com indicadores visuais (Online / Warning / Critical)
- 🔔 **Central de Alertas** — incidentes gerados automaticamente com base em thresholds operacionais, com ação de resolução integrada
- 📊 **Métricas Prometheus** — endpoint `/metrics` compatível com Prometheus para scraping externo
- 📖 **API REST Documentada** — Swagger UI integrado em `/docs` com especificação OpenAPI 3.0
- 🔐 **Autenticação JWT** — geração e validação de tokens de acesso para operações seguras
- 🐳 **Stack Completa via Docker Compose** — Postgres, FastAPI, Next.js, Prometheus e Grafana em um único `docker compose up`
- 🗄️ **Modo SQLite Local** — servidor autônomo sem dependências externas para desenvolvimento e demonstração

---

## 🛠️ Tecnologias Utilizadas

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| **Backend** | Python 3.11 + FastAPI | API REST assíncrona, alta performance |
| **Autenticação** | JWT + Passlib (Bcrypt) | Tokens de acesso e hash seguro de senhas |
| **ORM / Banco** | SQLAlchemy + PostgreSQL 15 | Persistência relacional de dados operacionais |
| **Dev / Demo** | SQLite (stdlib Python) | Banco embutido, zero configuração |
| **Métricas** | `prometheus-fastapi-instrumentator` | Exportação nativa para Prometheus |
| **Dashboards** | Grafana 10+ | Visualização e alertas de métricas |
| **Frontend** | Next.js 14 + React | Interface SPA moderna |
| **UI/Estilo** | Tailwind CSS + Chart.js | Design dark mode responsivo |
| **Orquestração** | Docker + Docker Compose | Stack completa em containers |

---

## 🗂️ Estrutura do Projeto

```
infrawatch/
├── 📄 docker-compose.yml          # Orquestração de todos os serviços
├── 🐍 server.py                   # Servidor autônomo Python (zero deps)
├── 📖 README.md
│
├── backend/                       # API FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                # Entrypoint + seed inicial
│       ├── core/
│       │   ├── config.py          # Variáveis de ambiente (Pydantic Settings)
│       │   ├── database.py        # Conexão SQLAlchemy
│       │   └── security.py        # JWT e hashing de senha
│       ├── models/
│       │   └── entities.py        # User, Server, MetricLog, Alert
│       ├── schemas/
│       │   └── schemas.py         # Validação Pydantic (request/response)
│       └── api/
│           ├── auth.py            # /auth — login, registro, /me
│           ├── monitoring.py      # /monitoring — servers, metrics, alerts
│           └── deps.py            # Injeção de dependências (auth guard)
│
├── frontend/                      # Interface Next.js 14
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.js
│   └── src/
│       ├── app/
│       │   ├── layout.js          # Root layout
│       │   ├── page.js            # Dashboard principal
│       │   └── globals.css
│       └── services/
│           └── api.js             # Integração Axios com a API
│
└── docker/
    ├── prometheus/
    │   └── prometheus.yml         # Configuração de scraping
    └── grafana/
        └── provisioning/          # Datasource automático (Prometheus)
```

---

## 🚀 Como Executar

### Opção 1 — Servidor Autônomo Python (recomendado para demo)

Roda com **zero dependências** além do Python 3.11+ nativo.

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/infrawatch.git
cd infrawatch

# Inicie o servidor
python3 server.py
```

Acesse em:

| Serviço | URL |
|---------|-----|
| 📊 **Dashboard** | http://localhost:8080 |
| 📖 **API Docs (Swagger)** | http://localhost:8080/docs |
| 📡 **Métricas Prometheus** | http://localhost:8080/metrics |

> **Credencial padrão:** `admin@infrawatch.io` / `admin123`

---

### Opção 2 — Stack Completa com Docker Compose

Requer Docker e Docker Compose instalados.

```bash
cd infrawatch
docker compose up -d --build
```

Todos os serviços sobem automaticamente:

| Serviço | URL | Descrição |
|---------|-----|-----------|
| 🌐 **Frontend** | http://localhost:3000 | Interface Next.js |
| ⚙️ **API (FastAPI)** | http://localhost:8000 | Backend Python |
| 📖 **Swagger UI** | http://localhost:8000/docs | Documentação interativa |
| 📡 **Prometheus** | http://localhost:9090 | Coleta de métricas |
| 📊 **Grafana** | http://localhost:3001 | Dashboards (`admin`/`admin`) |
| 🗄️ **PostgreSQL** | localhost:5432 | Banco de dados |

---

### Opção 3 — Desenvolvimento Local (sem Docker)

**Backend:**
```bash
cd infrawatch/backend
python3 -m venv venv
source venv/bin/activate       # Linux/macOS
# ou: venv\Scripts\activate    # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd infrawatch/frontend
npm install
npm run dev
```

---

## 📡 Endpoints da API

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/auth/register` | Cadastrar novo usuário |
| `POST` | `/api/v1/auth/login` | Login e geração de token JWT |
| `GET`  | `/api/v1/auth/me` | Dados do usuário autenticado |

### Monitoramento

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/v1/monitoring/overview` | KPIs do dashboard (totais e médias) |
| `GET`  | `/api/v1/monitoring/servers` | Listar todos os servidores |
| `POST` | `/api/v1/monitoring/servers` | Cadastrar novo servidor |
| `DELETE` | `/api/v1/monitoring/servers/{id}` | Remover servidor |
| `POST` | `/api/v1/monitoring/metrics` | Enviar métrica de um servidor |
| `GET`  | `/api/v1/monitoring/metrics/server/{id}` | Histórico de métricas do servidor |
| `GET`  | `/api/v1/monitoring/alerts` | Listar alertas operacionais |
| `PUT`  | `/api/v1/monitoring/alerts/{id}/resolve` | Resolver um alerta |
| `GET`  | `/metrics` | Métricas no formato Prometheus |

---

## 🔐 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do `backend/` ou configure via Docker Compose:

```env
# Banco de dados
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=infrawatch
POSTGRES_PORT=5432

# JWT
SECRET_KEY=sua-chave-secreta-jwt-muito-segura

# Modo SQLite (dev sem Postgres)
DB_TYPE=sqlite
```

---

## 📈 Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                        INFRAWATCH                            │
│                                                              │
│  ┌─────────────┐    HTTP/REST    ┌─────────────────────┐    │
│  │  Next.js 14 │◄──────────────►│   FastAPI (Python)  │    │
│  │  Dashboard  │                │   JWT + SQLAlchemy  │    │
│  └─────────────┘                └────────┬────────────┘    │
│                                          │                   │
│                              ┌───────────┴──────────┐       │
│                              │                       │       │
│                    ┌─────────▼──────┐  ┌────────────▼────┐  │
│                    │  PostgreSQL 15 │  │  /metrics (Prom) │  │
│                    │  (produção)    │  │                  │  │
│                    └────────────────┘  └────────┬────────┘  │
│                                                 │            │
│                                        ┌────────▼────────┐  │
│                                        │   Prometheus    │  │
│                                        │   + Grafana     │  │
│                                        └─────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Demonstração

> **5 servidores pré-configurados**, métricas históricas populadas automaticamente e telemetria simulada a cada 6 segundos — tudo disponível desde o primeiro acesso.

Servidores de exemplo incluídos:

| Servidor | Ambiente | Status inicial |
|----------|----------|----------------|
| `prod-k8s-master-01` | production | 🟢 Online |
| `prod-k8s-worker-01` | production | 🟢 Online |
| `prod-db-postgres-01` | production | 🟡 Warning |
| `staging-api-gateway` | staging | 🟢 Online |
| `redis-cache-cluster` | production | 🟢 Online |

---

## 📌 Resultado & Aprendizados

- ✅ Plataforma capaz de centralizar informações operacionais em um único dashboard
- ✅ Redução da complexidade no acompanhamento de infraestrutura e serviços
- ✅ Base para monitoramento proativo através de métricas, logs e alertas inteligentes
- ✅ Consolidação prática de conhecimentos em Cloud, DevOps, Observabilidade e Desenvolvimento Backend
- ✅ Projeto desenvolvido como laboratório de aprendizado para aplicação de boas práticas de infraestrutura moderna e automação

---

## 👨‍💻 Autor

Desenvolvido por **Ewerton** como projeto de laboratório pessoal para consolidação de conhecimentos em:

`Cloud Computing` · `DevOps` · `Observabilidade` · `Backend Python` · `Infraestrutura Moderna`

---

<div align="center">

**⭐ Se este projeto foi útil, deixe uma estrela!**

</div>
