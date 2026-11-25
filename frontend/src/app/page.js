'use client';

import React, { useState, useEffect } from 'react';
import { 
  Activity, Server, AlertTriangle, ShieldCheck, 
  Cpu, RefreshCw, Plus, LogOut, CheckCircle2,
  BarChart3, Layers, Trash2
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { monitoringService, authService } from '../services/api';

export default function Dashboard() {
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loginEmail, setLoginEmail] = useState('admin@infrawatch.io');
  const [loginPassword, setLoginPassword] = useState('admin123');
  const [loginError, setLoginError] = useState('');

  const [overview, setOverview] = useState({
    total_servers: 5,
    healthy_servers: 4,
    warning_servers: 1,
    critical_servers: 0,
    total_active_alerts: 1,
    average_cpu: 45.2,
    average_memory: 58.7,
  });

  const [servers, setServers] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [serverMetrics, setServerMetrics] = useState([]);
  const [showAddServerModal, setShowAddServerModal] = useState(false);
  const [newServer, setNewServer] = useState({ name: '', hostname: '', ip_address: '', environment: 'production' });

  useEffect(() => {
    const savedToken = localStorage.getItem('infrawatch_token');
    if (savedToken) {
      setToken(savedToken);
      fetchDashboardData();
    } else {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    const interval = setInterval(async () => {
      await monitoringService.simulateTick().catch(() => null);
      fetchDashboardData();
    }, 6000);
    return () => clearInterval(interval);
  }, [token, selectedServer?.id]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const data = await authService.login(loginEmail, loginPassword);
      localStorage.setItem('infrawatch_token', data.access_token);
      setToken(data.access_token);
      fetchDashboardData();
    } catch (err) {
      setLoginError('Credenciais inválidas. Tente admin@infrawatch.io / admin123');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('infrawatch_token');
    setToken(null);
  };

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [ovData, srvData, altData] = await Promise.all([
        monitoringService.getOverview().catch(() => null),
        monitoringService.getServers().catch(() => []),
        monitoringService.getAlerts().catch(() => [])
      ]);

      if (ovData) setOverview(ovData);
      if (srvData && srvData.length > 0) {
        setServers(srvData);
        const target = selectedServer
          ? srvData.find((s) => s.id === selectedServer.id) || srvData[0]
          : srvData[0];
        setSelectedServer(target);
        loadMetrics(target.id);
      } else {
        setServers([]);
        setSelectedServer(null);
        setServerMetrics([]);
      }
      if (altData) setAlerts(altData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async (serverId) => {
    try {
      const metrics = await monitoringService.getServerMetrics(serverId);
      const formatted = metrics.map((m) => ({
        time: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        cpu: m.cpu_percent,
        memoria: m.memory_percent,
        disco: m.disk_percent
      }));
      setServerMetrics(formatted);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectServer = (server) => {
    setSelectedServer(server);
    loadMetrics(server.id);
  };

  const handleResolveAlert = async (alertId) => {
    try {
      await monitoringService.resolveAlert(alertId);
      setAlerts(alerts.map(a => a.id === alertId ? { ...a, resolved: true } : a));
      setOverview(prev => ({ ...prev, total_active_alerts: Math.max(0, prev.total_active_alerts - 1) }));
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateServer = async (e) => {
    e.preventDefault();
    try {
      const created = await monitoringService.createServer(newServer);
      setServers([...servers, created]);
      setShowAddServerModal(false);
      setNewServer({ name: '', hostname: '', ip_address: '', environment: 'production' });
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteServer = async (e, serverId) => {
    e.stopPropagation();
    try {
      await monitoringService.deleteServer(serverId);
      const remaining = servers.filter((s) => s.id !== serverId);
      setServers(remaining);
      if (selectedServer?.id === serverId) {
        if (remaining.length > 0) {
          setSelectedServer(remaining[0]);
          loadMetrics(remaining[0].id);
        } else {
          setSelectedServer(null);
          setServerMetrics([]);
        }
      }
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    }
  };

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="w-full max-w-md p-8 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-blue-600/20 text-blue-500 rounded-xl">
              <Activity className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-wide">InfraWatch</h1>
              <p className="text-xs text-gray-400">Observabilidade & Monitoramento Cloud</p>
            </div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">E-mail Operacional</label>
              <input
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Senha</label>
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            {loginError && <p className="text-red-400 text-sm">{loginError}</p>}

            <button
              type="submit"
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-600/30"
            >
              Acessar Painel
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-gray-800 text-center text-xs text-gray-500">
            Padrão inicial: <span className="text-gray-300">admin@infrawatch.io</span> / <span className="text-gray-300">admin123</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Top Header */}
      <header className="border-b border-gray-800 bg-gray-900/60 backdrop-blur sticky top-0 z-20 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-lg text-white tracking-wide">InfraWatch</span>
            <span className="ml-2 text-xs px-2 py-0.5 bg-blue-950 text-blue-400 border border-blue-800 rounded-full font-mono">v1.0-Python</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={fetchDashboardData}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-sm text-gray-200 rounded-lg border border-gray-700 transition"
          >
            <RefreshCw className="w-4 h-4" />
            Atualizar
          </button>
          <a
            href="http://localhost:3001"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-600/20 text-orange-400 hover:bg-orange-600/30 text-sm rounded-lg border border-orange-700/50 transition font-medium"
          >
            <BarChart3 className="w-4 h-4" />
            Grafana
          </a>
          <button 
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-950/40 hover:bg-red-900/60 text-sm text-red-300 rounded-lg border border-red-900/60 transition"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        
        {/* Metric Cards Top Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-gray-900/90 border border-gray-800 rounded-xl">
            <div className="flex items-center justify-between text-gray-400 text-xs font-medium uppercase tracking-wider">
              <span>Total de Servidores</span>
              <Server className="w-4 h-4 text-blue-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-white">{overview.total_servers}</div>
            <div className="mt-1 text-xs text-gray-500">Monitorados via Prometheus</div>
          </div>

          <div className="p-4 bg-gray-900/90 border border-gray-800 rounded-xl">
            <div className="flex items-center justify-between text-gray-400 text-xs font-medium uppercase tracking-wider">
              <span>Status Operacional</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-emerald-400">{overview.healthy_servers} Online</div>
            <div className="mt-1 text-xs text-yellow-400">{overview.warning_servers} em alerta / {overview.critical_servers} crítico</div>
          </div>

          <div className="p-4 bg-gray-900/90 border border-gray-800 rounded-xl">
            <div className="flex items-center justify-between text-gray-400 text-xs font-medium uppercase tracking-wider">
              <span>Uso Médio de CPU</span>
              <Cpu className="w-4 h-4 text-purple-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-white">{overview.average_cpu}%</div>
            <div className="mt-1 text-xs text-gray-500">Memória média: {overview.average_memory}%</div>
          </div>

          <div className="p-4 bg-gray-900/90 border border-gray-800 rounded-xl">
            <div className="flex items-center justify-between text-gray-400 text-xs font-medium uppercase tracking-wider">
              <span>Alertas Pendentes</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-amber-400">{overview.total_active_alerts}</div>
            <div className="mt-1 text-xs text-gray-500">Ações prioritárias</div>
          </div>
        </div>

        {/* Charts & Server Details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Servidores List */}
          <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-5 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-400" />
                Nós e Máquinas
              </h2>
              <button 
                onClick={() => setShowAddServerModal(true)}
                className="p-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs flex items-center gap-1 font-medium transition"
              >
                <Plus className="w-3.5 h-3.5" /> Adicionar
              </button>
            </div>

            <div className="space-y-2 overflow-y-auto max-h-[420px] pr-1">
              {servers.map((s) => (
                <div
                  key={s.id}
                  onClick={() => handleSelectServer(s)}
                  className={`p-3.5 rounded-lg border cursor-pointer transition flex items-center justify-between ${
                    selectedServer?.id === s.id
                      ? 'bg-blue-950/40 border-blue-600/70 shadow-sm'
                      : 'bg-gray-800/40 border-gray-800 hover:border-gray-700'
                  }`}
                >
                  <div>
                    <div className="font-medium text-sm text-white flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${s.status === 'ONLINE' ? 'bg-emerald-400' : s.status === 'WARNING' ? 'bg-amber-400' : 'bg-red-500'}`}></span>
                      {s.name}
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">{s.ip_address} • {s.environment}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold ${
                      s.status === 'ONLINE' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                      s.status === 'WARNING' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                      'bg-red-950 text-red-400 border border-red-800'
                    }`}>
                      {s.status}
                    </span>
                    <button
                      onClick={(e) => handleDeleteServer(e, s.id)}
                      title="Remover servidor"
                      className="p-1 text-gray-500 hover:text-red-400 rounded transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Metric Chart */}
          <div className="lg:col-span-2 bg-gray-900/90 border border-gray-800 rounded-xl p-5 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  Métricas em Tempo Real — {selectedServer ? selectedServer.name : 'Selecione um nó'}
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">{selectedServer ? `${selectedServer.hostname} (${selectedServer.ip_address})` : 'Telemetry stream'}</p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <span className="flex items-center gap-1.5 text-blue-400 font-medium">
                  <span className="w-2.5 h-2.5 bg-blue-500 rounded-sm"></span> CPU (%)
                </span>
                <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <span className="w-2.5 h-2.5 bg-emerald-500 rounded-sm"></span> Memória (%)
                </span>
              </div>
            </div>

            <div className="w-full h-[320px]">
              {serverMetrics.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={serverMetrics}>
                    <defs>
                      <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={11} />
                    <YAxis stroke="#6b7280" fontSize={11} domain={[0, 100]} />
                    <Tooltip contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px', fontSize: '12px' }} />
                    <Area type="monotone" dataKey="cpu" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#cpuGradient)" />
                    <Area type="monotone" dataKey="memoria" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#memGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                  Coletando métricas do servidor...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Alerts Center */}
        <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Central de Incidentes & Alertas Operacionais
          </h2>
          <div className="divide-y divide-gray-800">
            {alerts.length === 0 ? (
              <p className="text-sm text-gray-500 py-3">Nenhum alerta registrado no momento. Sistema estável.</p>
            ) : (
              alerts.map((a) => (
                <div key={a.id} className="py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                      a.severity === 'CRITICAL' ? 'bg-red-950 text-red-400 border border-red-800' : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}>
                      {a.severity}
                    </span>
                    <div>
                      <p className={`text-sm ${a.resolved ? 'text-gray-500 line-through' : 'text-gray-200'}`}>{a.message}</p>
                      <span className="text-xs text-gray-500">{new Date(a.created_at).toLocaleString()}</span>
                    </div>
                  </div>

                  {!a.resolved && (
                    <button
                      onClick={() => handleResolveAlert(a.id)}
                      className="text-xs px-3 py-1.5 bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-800 rounded-lg flex items-center gap-1 transition"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Resolver
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

      </main>

      {/* Modal Adicionar Servidor */}
      {showAddServerModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-bold text-white mb-4">Registrar Novo Nó / Servidor</h3>
            <form onSubmit={handleCreateServer} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Nome do Recurso</label>
                <input
                  type="text"
                  placeholder="ex: prod-api-cluster-01"
                  value={newServer.name}
                  onChange={(e) => setNewServer({ ...newServer, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Hostname FQDN</label>
                <input
                  type="text"
                  placeholder="ex: srv-01.prod.cloud"
                  value={newServer.hostname}
                  onChange={(e) => setNewServer({ ...newServer, hostname: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Endereço IP</label>
                <input
                  type="text"
                  placeholder="ex: 10.0.4.15"
                  value={newServer.ip_address}
                  onChange={(e) => setNewServer({ ...newServer, ip_address: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Ambiente</label>
                <select
                  value={newServer.environment}
                  onChange={(e) => setNewServer({ ...newServer, environment: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
                >
                  <option value="production">production</option>
                  <option value="staging">staging</option>
                  <option value="development">development</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddServerModal(false)}
                  className="px-4 py-2 bg-gray-800 text-gray-300 rounded-lg text-sm hover:bg-gray-700 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-500 transition font-medium"
                >
                  Cadastrar Servidor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
