import http.server
import socketserver
import json
import sqlite3
import hashlib
import hmac
import base64
import time
import os
import random
from urllib.parse import urlparse
from datetime import datetime, timedelta

PORT = int(os.environ.get("PORT", 8080))

# Bug #4 fix: usar caminho absoluto para o banco, relativo ao script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "infrawatch_local.db")
SECRET_KEY = b"infrawatch-jwt-secret-key-2026"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            full_name TEXT,
            password_hash TEXT,
            role TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            hostname TEXT,
            ip_address TEXT,
            environment TEXT,
            status TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            severity TEXT,
            message TEXT,
            resolved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # Usuário admin padrão
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (id, email, full_name, password_hash, role) VALUES (1, 'admin@infrawatch.io', 'InfraWatch Admin', ?, 'admin')", (admin_hash,))

    # Servidores de exemplo
    c.execute("SELECT count(*) FROM servers")
    if c.fetchone()[0] == 0:
        default_servers = [
            ("prod-k8s-master-01", "k8s-m1.prod.local",    "192.168.10.10", "production", "ONLINE"),
            ("prod-k8s-worker-01", "k8s-w1.prod.local",    "192.168.10.11", "production", "ONLINE"),
            ("prod-db-postgres-01","pg-primary.prod.local", "192.168.10.20", "production", "WARNING"),
            ("staging-api-gateway","gw-stg.internal",       "192.168.20.15", "staging",    "ONLINE"),
            ("redis-cache-cluster","redis-01.prod.local",   "192.168.10.30", "production", "ONLINE"),
        ]
        c.executemany("INSERT INTO servers (name, hostname, ip_address, environment, status) VALUES (?,?,?,?,?)", default_servers)

        # Métricas históricas com timestamps ISO corretos (Bug #9 fix)
        now_ts = datetime.utcnow()
        for s_id in range(1, 6):
            base_cpu = 32.0 if s_id != 3 else 82.5
            base_mem = 44.0 if s_id != 3 else 88.0
            for i in range(20):
                ts = (now_ts - timedelta(minutes=20 - i)).strftime("%Y-%m-%dT%H:%M:%S")
                cpu = round(max(5.0, min(99.0, base_cpu + random.uniform(-8, 12))), 1)
                mem = round(max(10.0, min(98.0, base_mem + random.uniform(-4, 6))), 1)
                c.execute(
                    "INSERT INTO metrics (server_id, cpu_percent, memory_percent, disk_percent, timestamp) VALUES (?,?,?,?,?)",
                    (s_id, cpu, mem, 62.4, ts)
                )

        c.execute("INSERT INTO alerts (server_id, severity, message, resolved) VALUES (3,'WARNING','Alto consumo de memória em prod-db-postgres-01 (> 85%)',0)")

    conn.commit()
    conn.close()


# Bug #1 fix: generate_jwt usando hmac.new corretamente
def generate_jwt(email: str) -> str:
    header  = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub":email,"exp":int(time.time())+86400}).encode()).rstrip(b"=").decode()
    msg     = f"{header}.{payload}".encode()
    sig_bytes = hmac.new(SECRET_KEY, msg, hashlib.sha256).digest()
    sig     = base64.urlsafe_b64encode(sig_bytes).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


# ─── HTML ───────────────────────────────────────────────────────────────────
HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InfraWatch — Monitoramento de Infraestrutura</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  <style>
    body { background:#0b0f19; color:#f3f4f6; font-family:system-ui,-apple-system,sans-serif; }
    ::-webkit-scrollbar { width:4px; } ::-webkit-scrollbar-thumb { background:#374151; border-radius:4px; }
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Header -->
  <header class="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-20 px-6 py-3.5 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="p-2 bg-blue-600/20 text-blue-400 rounded-lg">
        <i class="fa-solid fa-chart-line text-lg"></i>
      </div>
      <div>
        <span class="font-bold text-lg text-white tracking-wide">InfraWatch</span>
        <span class="ml-2 text-xs px-2 py-0.5 bg-blue-950 text-blue-400 border border-blue-800 rounded-full font-mono">Python-Engine v2</span>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <span id="lastUpdate" class="text-[11px] text-gray-500 mr-2"></span>
      <a href="/metrics" target="_blank" class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600/20 text-amber-400 hover:bg-amber-600/30 text-xs rounded-lg border border-amber-700/50 transition font-medium">
        <i class="fa-solid fa-database"></i> /metrics
      </a>
      <a href="/docs" target="_blank" class="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 text-xs rounded-lg border border-emerald-700/50 transition font-medium">
        <i class="fa-solid fa-code"></i> API Docs
      </a>
      <button onclick="refreshAll()" class="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-xs text-gray-200 rounded-lg border border-gray-700 transition">
        <i id="refreshIcon" class="fa-solid fa-rotate-right"></i> Atualizar
      </button>
    </div>
  </header>

  <!-- Main -->
  <main class="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">

    <!-- KPI Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="p-4 bg-gray-900 border border-gray-800 rounded-xl">
        <div class="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider">
          <span>Servidores</span><i class="fa-solid fa-server text-blue-400"></i>
        </div>
        <div id="totalServers" class="mt-2 text-3xl font-bold text-white">—</div>
        <div class="mt-1 text-xs text-gray-500">Monitorados ativamente</div>
      </div>

      <div class="p-4 bg-gray-900 border border-gray-800 rounded-xl">
        <div class="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider">
          <span>Operacional</span><i class="fa-solid fa-shield-halved text-emerald-400"></i>
        </div>
        <div id="healthyServers" class="mt-2 text-3xl font-bold text-emerald-400">—</div>
        <div id="warningCount" class="mt-1 text-xs text-amber-400">—</div>
      </div>

      <div class="p-4 bg-gray-900 border border-gray-800 rounded-xl">
        <div class="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider">
          <span>CPU Média</span><i class="fa-solid fa-microchip text-purple-400"></i>
        </div>
        <div id="avgCpu" class="mt-2 text-3xl font-bold text-white">—</div>
        <div id="avgMem" class="mt-1 text-xs text-gray-500">— mem</div>
      </div>

      <div class="p-4 bg-gray-900 border border-gray-800 rounded-xl">
        <div class="flex items-center justify-between text-gray-400 text-xs font-semibold uppercase tracking-wider">
          <span>Alertas</span><i class="fa-solid fa-triangle-exclamation text-amber-400"></i>
        </div>
        <div id="activeAlerts" class="mt-2 text-3xl font-bold text-amber-400">—</div>
        <div class="mt-1 text-xs text-gray-500">Incidentes em aberto</div>
      </div>
    </div>

    <!-- Nodes + Chart -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- Server List -->
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <i class="fa-solid fa-network-wired text-blue-400"></i> Nós do Cluster
          </h2>
          <button onclick="openModal()" class="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium flex items-center gap-1 transition">
            <i class="fa-solid fa-plus"></i> Novo Nó
          </button>
        </div>
        <div id="serverList" class="space-y-2 overflow-y-auto max-h-[400px] pr-1">
          <p class="text-xs text-gray-500 py-4 text-center">Carregando servidores...</p>
        </div>
      </div>

      <!-- Chart -->
      <div class="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h2 id="chartTitle" class="text-base font-semibold text-white flex items-center gap-2">
              <i class="fa-solid fa-wave-square text-emerald-400"></i> Telemetria em Tempo Real
            </h2>
            <p id="chartSubtitle" class="text-xs text-gray-400 mt-0.5">Selecione um servidor</p>
          </div>
          <div class="flex items-center gap-4 text-xs font-medium">
            <span class="flex items-center gap-1.5 text-blue-400"><span class="w-2.5 h-2.5 bg-blue-500 rounded-sm inline-block"></span> CPU</span>
            <span class="flex items-center gap-1.5 text-emerald-400"><span class="w-2.5 h-2.5 bg-emerald-500 rounded-sm inline-block"></span> Memória</span>
          </div>
        </div>
        <div class="relative flex-1 min-h-[260px]">
          <canvas id="metricsChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Alerts -->
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h2 class="text-sm font-semibold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
        <i class="fa-solid fa-bell text-amber-400"></i> Central de Incidentes & Alertas
      </h2>
      <div id="alertsList" class="divide-y divide-gray-800 min-h-[48px]">
        <p class="text-xs text-gray-500 py-3">Carregando alertas...</p>
      </div>
    </div>

  </main>

  <!-- Modal -->
  <div id="addModal" class="hidden fixed inset-0 bg-black/75 flex items-center justify-center p-4 z-50">
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
      <h3 class="text-base font-bold text-white mb-4">Registrar Novo Servidor</h3>
      <div class="space-y-3">
        <div>
          <label class="block text-xs text-gray-400 mb-1">Nome</label>
          <input id="srvName" type="text" placeholder="ex: prod-worker-02" class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500">
        </div>
        <div>
          <label class="block text-xs text-gray-400 mb-1">Hostname FQDN</label>
          <input id="srvHost" type="text" placeholder="ex: worker-02.prod.local" class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500">
        </div>
        <div>
          <label class="block text-xs text-gray-400 mb-1">Endereço IP</label>
          <input id="srvIp" type="text" placeholder="ex: 192.168.10.15" class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500">
        </div>
        <div>
          <label class="block text-xs text-gray-400 mb-1">Ambiente</label>
          <select id="srvEnv" class="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white">
            <option value="production">production</option>
            <option value="staging">staging</option>
            <option value="development">development</option>
          </select>
        </div>
      </div>
      <div id="modalError" class="hidden mt-2 text-xs text-red-400"></div>
      <div class="flex justify-end gap-2 mt-5">
        <button onclick="closeModal()" class="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs transition">Cancelar</button>
        <button onclick="submitServer()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition">Cadastrar</button>
      </div>
    </div>
  </div>

<script>
  // ── State ──────────────────────────────────────────────────────────────
  let selectedServerId = 1;
  let chartInstance    = null;
  let isFetching       = false;        // Bug #3 fix: evitar requisições concorrentes

  // ── Chart Init (Bug #8 fix: protege contra múltiplos inits) ───────────
  function initChart() {
    if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
    const ctx = document.getElementById('metricsChart').getContext('2d');
    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'CPU (%)',
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59,130,246,0.12)',
            borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2, data: []
          },
          {
            label: 'Memória (%)',
            borderColor: '#10b981',
            backgroundColor: 'rgba(16,185,129,0.12)',
            borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2, data: []
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        scales: {
          y: { min: 0, max: 100, grid: { color: '#1f2937' }, ticks: { color: '#9ca3af', font: { size: 10 } } },
          x: { grid: { color: '#111827' }, ticks: { color: '#6b7280', font: { size: 10 }, maxTicksLimit: 8 } }
        },
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } }
      }
    });
  }

  // Bug #9 fix: parsear timestamps SQLite corretamente (substitui espaço por T)
  function parseDate(str) {
    if (!str) return new Date();
    // SQLite retorna "2026-11-24 22:30:19" — browsers exigem ISO "2026-11-24T22:30:19"
    return new Date(str.replace(' ', 'T') + 'Z');
  }

  // ── Render KPIs ────────────────────────────────────────────────────────
  function renderOverview(ov) {
    document.getElementById('totalServers').innerText   = ov.total_servers;
    document.getElementById('healthyServers').innerText = `${ov.healthy_servers} Online`;
    document.getElementById('warningCount').innerText   = `${ov.warning_servers} alerta • ${ov.critical_servers} crítico`;
    document.getElementById('avgCpu').innerText         = `${ov.average_cpu}%`;
    document.getElementById('avgMem').innerText         = `${ov.average_memory}% mem`;
    document.getElementById('activeAlerts').innerText   = ov.total_active_alerts;
  }

  // ── Render Server List ─────────────────────────────────────────────────
  // Bug #2 fix: renderServers NÃO chama selectServer automaticamente a cada atualização
  function renderServers(list) {
    const container = document.getElementById('serverList');
    if (!list || list.length === 0) {
      container.innerHTML = '<p class="text-xs text-gray-500 py-4 text-center">Nenhum servidor cadastrado.</p>';
      return;
    }
    container.innerHTML = '';
    list.forEach(s => {
      const isSelected = s.id === selectedServerId;
      const statusClasses = {
        ONLINE:   { dot: 'bg-emerald-400', badge: 'bg-emerald-950 text-emerald-400 border-emerald-800' },
        WARNING:  { dot: 'bg-amber-400',   badge: 'bg-amber-950   text-amber-400   border-amber-800'   },
        CRITICAL: { dot: 'bg-red-500',     badge: 'bg-red-950     text-red-400     border-red-800'     },
      }[s.status] || { dot: 'bg-gray-500', badge: 'bg-gray-800 text-gray-400 border-gray-700' };

      const card = document.createElement('div');
      card.dataset.serverId = s.id;
      card.className = `p-3 rounded-lg border cursor-pointer transition flex items-center justify-between ${
        isSelected ? 'bg-blue-950/50 border-blue-600/60' : 'bg-gray-800/40 border-gray-800 hover:border-gray-600'
      }`;
      card.onclick = () => selectServer(s);
      card.innerHTML = `
        <div class="min-w-0 flex-1">
          <div class="font-medium text-xs text-white flex items-center gap-2 truncate">
            <span class="shrink-0 w-2 h-2 rounded-full ${statusClasses.dot}"></span>
            <span class="truncate">${s.name}</span>
          </div>
          <div class="text-[11px] text-gray-400 mt-0.5 ml-4">${s.ip_address} · ${s.environment}</div>
        </div>
        <span class="ml-2 shrink-0 text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold border ${statusClasses.badge}">
          ${s.status}
        </span>`;
      container.appendChild(card);
    });
  }

  // ── Select Server & Load Metrics ───────────────────────────────────────
  async function selectServer(server) {
    selectedServerId = server.id;
    document.getElementById('chartTitle').innerHTML = `<i class="fa-solid fa-wave-square text-emerald-400"></i> ${server.name}`;
    document.getElementById('chartSubtitle').innerText = `${server.hostname} (${server.ip_address}) · ${server.environment}`;

    // Re-renderiza lista para atualizar seleção destacada (sem re-fetch de servidores)
    document.querySelectorAll('#serverList > div').forEach(el => {
      const isNow = Number(el.dataset.serverId) === server.id;
      el.className = el.className.replace(/bg-blue-950\\/50 border-blue-600\\/60|bg-gray-800\\/40 border-gray-800 hover:border-gray-600/, '');
      el.classList.add(...(isNow
        ? ['bg-blue-950/50', 'border-blue-600/60']
        : ['bg-gray-800/40', 'border-gray-800', 'hover:border-gray-600']));
    });

    try {
      const metrics = await fetch(`/api/v1/monitoring/metrics/server/${server.id}`).then(r => r.json());
      if (!chartInstance) initChart();
      // Bug #9 fix: usar parseDate para timestamps do SQLite
      chartInstance.data.labels            = metrics.map(m => parseDate(m.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}));
      chartInstance.data.datasets[0].data  = metrics.map(m => m.cpu_percent);
      chartInstance.data.datasets[1].data  = metrics.map(m => m.memory_percent);
      chartInstance.update('none');
    } catch (err) {
      console.error('Erro ao carregar métricas:', err);
    }
  }

  // ── Render Alerts ──────────────────────────────────────────────────────
  function renderAlerts(list) {
    const container = document.getElementById('alertsList');
    if (!list || list.length === 0) {
      container.innerHTML = '<p class="text-xs text-gray-500 py-3">Sistema estável — nenhum incidente ativo.</p>';
      return;
    }
    container.innerHTML = '';
    list.forEach(a => {
      const badge = a.severity === 'CRITICAL'
        ? 'bg-red-950 text-red-400 border border-red-800'
        : 'bg-amber-950 text-amber-400 border border-amber-800';
      const row = document.createElement('div');
      row.className = 'py-3 flex items-center justify-between gap-3';
      // Bug #9 fix: usar parseDate
      const dateStr = parseDate(a.created_at).toLocaleString('pt-BR');
      row.innerHTML = `
        <div class="flex items-start gap-3 min-w-0">
          <span class="shrink-0 mt-0.5 text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${badge}">${a.severity}</span>
          <div class="min-w-0">
            <p class="text-xs ${a.resolved ? 'text-gray-500 line-through' : 'text-gray-200'} break-words">${a.message}</p>
            <span class="text-[10px] text-gray-500">${dateStr}</span>
          </div>
        </div>
        ${!a.resolved ? `
        <button onclick="resolveAlert(${a.id})" class="shrink-0 text-xs px-2.5 py-1 bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 rounded-lg flex items-center gap-1 transition">
          <i class="fa-solid fa-check"></i> Resolver
        </button>` : '<span class="shrink-0 text-xs text-gray-600 font-medium">Resolvido</span>'}`;
      container.appendChild(row);
    });
  }

  // ── Refresh All (Bug #2 e #3 fix: um único fetch coordenado) ──────────
  async function refreshAll() {
    if (isFetching) return;          // evita sobreposição de chamadas
    isFetching = true;
    document.getElementById('refreshIcon').classList.add('fa-spin');

    try {
      const [ov, servers, alerts] = await Promise.all([
        fetch('/api/v1/monitoring/overview').then(r => r.json()),
        fetch('/api/v1/monitoring/servers').then(r => r.json()),
        fetch('/api/v1/monitoring/alerts').then(r => r.json()),
      ]);

      renderOverview(ov);
      renderServers(servers);
      renderAlerts(alerts);

      // Atualiza métricas do servidor selecionado
      const sel = servers.find(s => s.id === selectedServerId) || servers[0];
      if (sel) await selectServer(sel);

      document.getElementById('lastUpdate').innerText = 'Atualizado: ' + new Date().toLocaleTimeString('pt-BR');
    } catch (err) {
      console.error('Erro ao atualizar dados:', err);
    } finally {
      isFetching = false;
      document.getElementById('refreshIcon').classList.remove('fa-spin');
    }
  }

  // ── Resolve Alert ──────────────────────────────────────────────────────
  async function resolveAlert(id) {
    try {
      await fetch(`/api/v1/monitoring/alerts/${id}/resolve`, { method: 'PUT' });
      refreshAll();
    } catch (err) {
      console.error('Erro ao resolver alerta:', err);
    }
  }

  // ── Modal ──────────────────────────────────────────────────────────────
  function openModal()  { document.getElementById('addModal').classList.remove('hidden'); }
  function closeModal() {
    document.getElementById('addModal').classList.add('hidden');
    document.getElementById('modalError').classList.add('hidden');
  }

  async function submitServer() {
    const name        = document.getElementById('srvName').value.trim();
    const hostname    = document.getElementById('srvHost').value.trim();
    const ip_address  = document.getElementById('srvIp').value.trim();
    const environment = document.getElementById('srvEnv').value;
    const errEl       = document.getElementById('modalError');

    if (!name || !hostname || !ip_address) {
      errEl.innerText = 'Preencha todos os campos obrigatórios.';
      errEl.classList.remove('hidden');
      return;
    }
    errEl.classList.add('hidden');

    try {
      const res = await fetch('/api/v1/monitoring/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, hostname, ip_address, environment }),
      });
      if (!res.ok) throw new Error('Falha ao cadastrar servidor');
      closeModal();
      ['srvName','srvHost','srvIp'].forEach(id => document.getElementById(id).value = '');
      refreshAll();
    } catch (err) {
      errEl.innerText = err.message;
      errEl.classList.remove('hidden');
    }
  }

  // ── Tick de telemetria + atualização periódica (Bug #3 fix) ───────────
  // Tick e refreshAll separados, sem chamadas aninhadas
  async function simulateTick() {
    try { await fetch('/api/v1/monitoring/simulate-tick', { method: 'POST' }); } catch (_) {}
  }

  // A cada 6s: simula tick, depois recarrega dados
  setInterval(async () => {
    await simulateTick();
    if (!isFetching) refreshAll();
  }, 6000);

  // ── Init ───────────────────────────────────────────────────────────────
  window.addEventListener('DOMContentLoaded', () => {
    initChart();
    refreshAll();
  });
</script>
</body>
</html>"""


# ─── Swagger Docs ────────────────────────────────────────────────────────────
SWAGGER_DOCS_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>InfraWatch API Docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
  <style> body { margin:0; background:#0b0f19; } </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: '/openapi.json',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      layout: 'BaseLayout',
      deepLinking: true,
    });
  </script>
</body>
</html>"""


# ─── OpenAPI Spec completo ───────────────────────────────────────────────────
OPENAPI_SPEC = {
  "openapi": "3.0.2",
  "info": {
    "title": "InfraWatch API",
    "description": "Plataforma de Observabilidade e Monitoramento de Infraestrutura — Python Engine",
    "version": "1.0.0"
  },
  "paths": {
    "/api/v1/monitoring/overview": {
      "get": {
        "summary": "Dashboard Overview KPIs",
        "description": "Retorna contadores gerais: servidores, alertas, médias de CPU e memória.",
        "responses": { "200": { "description": "Overview retornado com sucesso" } }
      }
    },
    "/api/v1/monitoring/servers": {
      "get":  { "summary": "Listar servidores", "responses": { "200": { "description": "Lista de servidores" } } },
      "post": {
        "summary": "Cadastrar servidor",
        "requestBody": {
          "required": True,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "required": ["name","hostname","ip_address"],
                "properties": {
                  "name":        { "type": "string" },
                  "hostname":    { "type": "string" },
                  "ip_address":  { "type": "string" },
                  "environment": { "type": "string", "enum": ["production","staging","development"] }
                }
              }
            }
          }
        },
        "responses": { "201": { "description": "Servidor criado" } }
      }
    },
    "/api/v1/monitoring/metrics/server/{server_id}": {
      "get": {
        "summary": "Métricas do servidor",
        "parameters": [{ "name": "server_id", "in": "path", "required": True, "schema": { "type": "integer" } }],
        "responses": { "200": { "description": "Lista de métricas" } }
      }
    },
    "/api/v1/monitoring/alerts": {
      "get": { "summary": "Listar alertas", "responses": { "200": { "description": "Lista de alertas" } } }
    },
    "/api/v1/monitoring/alerts/{alert_id}/resolve": {
      "put": {
        "summary": "Resolver alerta",
        "parameters": [{ "name": "alert_id", "in": "path", "required": True, "schema": { "type": "integer" } }],
        "responses": { "200": { "description": "Alerta resolvido" } }
      }
    },
    "/api/v1/monitoring/simulate-tick": {
      "post": { "summary": "Simular tick de telemetria", "responses": { "200": { "description": "Tick executado" } } }
    },
    "/metrics": {
      "get": { "summary": "Métricas Prometheus", "description": "Formato exposition text compatível com Prometheus.", "responses": { "200": { "description": "Métricas em formato texto" } } }
    }
  }
}


# ─── Handler HTTP ────────────────────────────────────────────────────────────
class RequestHandler(http.server.BaseHTTPRequestHandler):

    # Bug #7 fix: silenciar logs HTTP verbosos
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, content_type="text/plain"):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # Bug #5 fix: 404 com Content-Type correto
    def send_404(self):
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            return self.send_html(HTML_PAGE)

        if path == "/docs":
            return self.send_html(SWAGGER_DOCS_HTML)

        if path == "/openapi.json":
            return self.send_json(OPENAPI_SPEC)

        if path == "/metrics":
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT count(*) FROM servers"); total_srv = c.fetchone()[0]
            c.execute("SELECT count(*) FROM servers WHERE status='ONLINE'"); online_srv = c.fetchone()[0]
            c.execute("SELECT count(*) FROM alerts WHERE resolved=0"); act_alerts = c.fetchone()[0]
            c.execute("SELECT avg(cpu_percent),avg(memory_percent) FROM metrics WHERE timestamp >= datetime('now','-15 minutes')")
            row = c.fetchone()
            avg_cpu = round(row[0] or 0.0, 2)
            avg_mem = round(row[1] or 0.0, 2)
            conn.close()
            prom = (
                f"# HELP infrawatch_servers_total Total de servidores\n"
                f"# TYPE infrawatch_servers_total gauge\n"
                f"infrawatch_servers_total {total_srv}\n\n"
                f"# HELP infrawatch_servers_online Servidores online\n"
                f"# TYPE infrawatch_servers_online gauge\n"
                f"infrawatch_servers_online {online_srv}\n\n"
                f"# HELP infrawatch_active_alerts Alertas ativos\n"
                f"# TYPE infrawatch_active_alerts gauge\n"
                f"infrawatch_active_alerts {act_alerts}\n\n"
                f"# HELP infrawatch_cluster_cpu_percent Media CPU cluster\n"
                f"# TYPE infrawatch_cluster_cpu_percent gauge\n"
                f"infrawatch_cluster_cpu_percent {avg_cpu}\n\n"
                f"# HELP infrawatch_cluster_memory_percent Media memoria cluster\n"
                f"# TYPE infrawatch_cluster_memory_percent gauge\n"
                f"infrawatch_cluster_memory_percent {avg_mem}\n"
            )
            return self.send_text(prom, "text/plain; version=0.0.4")

        if path == "/api/v1/monitoring/overview":
            conn = sqlite3.connect(DB_FILE); c = conn.cursor()
            c.execute("SELECT count(*) FROM servers"); total = c.fetchone()[0]
            c.execute("SELECT count(*) FROM servers WHERE status='ONLINE'");   healthy  = c.fetchone()[0]
            c.execute("SELECT count(*) FROM servers WHERE status='WARNING'");  warning  = c.fetchone()[0]
            c.execute("SELECT count(*) FROM servers WHERE status='CRITICAL'"); critical = c.fetchone()[0]
            c.execute("SELECT count(*) FROM alerts WHERE resolved=0"); alerts = c.fetchone()[0]
            c.execute("SELECT avg(cpu_percent),avg(memory_percent) FROM metrics WHERE timestamp>=datetime('now','-15 minutes')")
            m = c.fetchone()
            conn.close()
            return self.send_json({
                "total_servers": total, "healthy_servers": healthy,
                "warning_servers": warning, "critical_servers": critical,
                "total_active_alerts": alerts,
                "average_cpu":    round(m[0] or 35.0, 1),
                "average_memory": round(m[1] or 48.0, 1)
            })

        if path == "/api/v1/monitoring/servers":
            conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; c = conn.cursor()
            c.execute("SELECT * FROM servers ORDER BY id ASC")
            rows = [dict(r) for r in c.fetchall()]; conn.close()
            return self.send_json(rows)

        if path.startswith("/api/v1/monitoring/metrics/server/"):
            try:
                server_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self.send_404()
            conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; c = conn.cursor()
            c.execute("SELECT * FROM metrics WHERE server_id=? ORDER BY id DESC LIMIT 20", (server_id,))
            rows = list(reversed([dict(r) for r in c.fetchall()])); conn.close()
            return self.send_json(rows)

        if path == "/api/v1/monitoring/alerts":
            conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row; c = conn.cursor()
            c.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 50")
            rows = [dict(r) for r in c.fetchall()]; conn.close()
            return self.send_json(rows)

        return self.send_404()

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("content-length", 0))
        raw = self.rfile.read(length) if length > 0 else b""

        if path == "/api/v1/monitoring/servers":
            try:
                payload = json.loads(raw)
                name       = payload["name"]
                hostname   = payload["hostname"]
                ip_address = payload["ip_address"]
                env        = payload.get("environment", "production")
            except (json.JSONDecodeError, KeyError) as e:
                return self.send_json({"error": str(e)}, 400)

            conn = sqlite3.connect(DB_FILE); c = conn.cursor()
            c.execute("INSERT INTO servers (name,hostname,ip_address,environment,status) VALUES (?,?,?,?,'ONLINE')",
                      (name, hostname, ip_address, env))
            new_id = c.lastrowid
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            c.execute("INSERT INTO metrics (server_id,cpu_percent,memory_percent,disk_percent,timestamp) VALUES (?,25.0,35.0,40.0,?)", (new_id, ts))
            conn.commit(); conn.close()
            return self.send_json({"id": new_id, "name": name, "status": "ONLINE"}, 201)

        # Bug #10 fix: simulate-tick limpa registros antigos antes de inserir
        if path == "/api/v1/monitoring/simulate-tick":  # noqa
            conn = sqlite3.connect(DB_FILE); c = conn.cursor()
            c.execute("SELECT id, status FROM servers")
            servers = c.fetchall()
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            for s_id, s_status in servers:
                base_c = 30.0 if s_status == "ONLINE" else 80.0
                base_m = 40.0 if s_status == "ONLINE" else 85.0
                cpu = round(max(5.0, min(99.0, base_c + random.uniform(-10, 15))), 1)
                mem = round(max(10.0, min(98.0, base_m + random.uniform(-5, 8))),  1)
                c.execute("INSERT INTO metrics (server_id,cpu_percent,memory_percent,disk_percent,timestamp) VALUES (?,?,?,60.0,?)",
                          (s_id, cpu, mem, ts))
                # Mantém apenas os últimos 100 registros por servidor
                c.execute("""DELETE FROM metrics WHERE server_id=? AND id NOT IN (
                              SELECT id FROM metrics WHERE server_id=? ORDER BY id DESC LIMIT 100
                             )""", (s_id, s_id))
            conn.commit(); conn.close()
            return self.send_json({"tick": True, "servers": len(servers)})

        if path == "/api/v1/monitoring/metrics":
            try:
                payload = json.loads(raw)
                server_id = int(payload["server_id"])
                cpu = float(payload["cpu_percent"])
                mem = float(payload["memory_percent"])
                disk = float(payload["disk_percent"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                return self.send_json({"error": str(e)}, 400)

            conn = sqlite3.connect(DB_FILE); c = conn.cursor()
            c.execute("SELECT id, name FROM servers WHERE id=?", (server_id,))
            srv = c.fetchone()
            if not srv:
                conn.close()
                return self.send_json({"error": "Servidor não encontrado"}, 404)

            ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            c.execute(
                "INSERT INTO metrics (server_id,cpu_percent,memory_percent,disk_percent,timestamp) VALUES (?,?,?,?,?)",
                (server_id, cpu, mem, disk, ts)
            )
            metric_id = c.lastrowid

            if cpu > 90 or mem > 90:
                new_status = "CRITICAL"
                c.execute(
                    "INSERT INTO alerts (server_id,severity,message,resolved) VALUES (?,?,?,0)",
                    (server_id, "CRITICAL", f"Consumo crítico no servidor {srv[1]}: CPU {cpu}%, Memória {mem}%")
                )
            elif cpu > 75 or mem > 80:
                new_status = "WARNING"
            else:
                new_status = "ONLINE"
            c.execute("UPDATE servers SET status=? WHERE id=?", (new_status, server_id))
            conn.commit(); conn.close()
            return self.send_json({
                "id": metric_id,
                "server_id": server_id,
                "cpu_percent": cpu,
                "memory_percent": mem,
                "disk_percent": disk,
                "timestamp": ts
            }, 201)

        if path == "/api/v1/auth/login":
            email = "admin@infrawatch.io"
            role = "admin"
            if raw:
                try:
                    creds = json.loads(raw)
                    email = creds.get("email") or creds.get("username") or email
                    password = creds.get("password")
                    if password is not None:
                        pw_hash = hashlib.sha256(password.encode()).hexdigest()
                        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
                        c.execute("SELECT email, role, password_hash FROM users WHERE email=?", (email,))
                        row = c.fetchone()
                        conn.close()
                        if not row or row[2] != pw_hash:
                            return self.send_json({"detail": "E-mail ou senha incorretos"}, 401)
                        role = row[1]
                except json.JSONDecodeError:
                    pass
            token = generate_jwt(email)
            return self.send_json({"access_token": token, "token_type": "bearer",
                                   "user": {"email": email, "role": role}})

        return self.send_404()

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/v1/monitoring/servers/"):
            try:
                server_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self.send_404()
            conn = sqlite3.connect(DB_FILE); c = conn.cursor()
            c.execute("SELECT id FROM servers WHERE id=?", (server_id,))
            if not c.fetchone():
                conn.close()
                return self.send_json({"error": "Servidor não encontrado"}, 404)
            c.execute("DELETE FROM metrics WHERE server_id=?", (server_id,))
            c.execute("DELETE FROM alerts WHERE server_id=?", (server_id,))
            c.execute("DELETE FROM servers WHERE id=?", (server_id,))
            conn.commit(); conn.close()
            return self.send_json({"message": "Servidor removido com sucesso"})

        return self.send_404()

    def do_PUT(self):
        path = urlparse(self.path).path
        # /api/v1/monitoring/alerts/{id}/resolve
        if path.startswith("/api/v1/monitoring/alerts/") and path.endswith("/resolve"):
            try:
                # Bug #6 verificado: extrai o ID corretamente
                parts = path.strip("/").split("/")
                # ['api','v1','monitoring','alerts', ID, 'resolve'] → parts[4]
                alert_id = int(parts[4])
            except (ValueError, IndexError):
                return self.send_404()
            conn = sqlite3.connect(DB_FILE); c = conn.cursor()
            c.execute("UPDATE alerts SET resolved=1 WHERE id=?", (alert_id,))
            conn.commit(); conn.close()
            return self.send_json({"id": alert_id, "resolved": True})

        return self.send_404()


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    init_db()
    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  InfraWatch — Plataforma de Monitoramento           ║")
    print(f"║  Dashboard  →  http://localhost:{PORT}                ║")
    print(f"║  API Docs   →  http://localhost:{PORT}/docs           ║")
    print(f"║  Metrics    →  http://localhost:{PORT}/metrics        ║")
    print(f"╚══════════════════════════════════════════════════════╝")
    with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
        httpd.serve_forever()
