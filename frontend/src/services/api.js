import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('infrawatch_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('infrawatch_token');
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const response = await api.post('/auth/login', formData);
    return response.data;
  },
  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  }
};

export const monitoringService = {
  getOverview: async () => {
    const response = await api.get('/monitoring/overview');
    return response.data;
  },
  getServers: async () => {
    const response = await api.get('/monitoring/servers');
    return response.data;
  },
  createServer: async (serverData) => {
    const response = await api.post('/monitoring/servers', serverData);
    return response.data;
  },
  deleteServer: async (serverId) => {
    const response = await api.delete(`/monitoring/servers/${serverId}`);
    return response.data;
  },
  getServerMetrics: async (serverId) => {
    const response = await api.get(`/monitoring/metrics/server/${serverId}`);
    return response.data;
  },
  simulateTick: async () => {
    const response = await api.post('/monitoring/simulate-tick');
    return response.data;
  },
  getAlerts: async () => {
    const response = await api.get('/monitoring/alerts');
    return response.data;
  },
  resolveAlert: async (alertId) => {
    const response = await api.put(`/monitoring/alerts/${alertId}/resolve`);
    return response.data;
  }
};
