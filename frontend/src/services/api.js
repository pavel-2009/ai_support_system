const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export const getStoredToken = () => localStorage.getItem('access_token');
export const setStoredTokens = (accessToken, refreshToken) => {
  if (accessToken) localStorage.setItem('access_token', accessToken);
  if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
};
export const clearStoredTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_info');
};

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;
  const tokens = await response.json();
  if (!tokens.access_token) return false;
  setStoredTokens(tokens.access_token, tokens.refresh_token);
  return true;
}

async function request(endpoint, options = {}, allowRefresh = true) {
  const token = getStoredToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    if (allowRefresh && !endpoint.includes('/auth/')) {
      try {
        if (await refreshAccessToken()) return request(endpoint, options, false);
      } catch {}
    }
    if (!endpoint.includes('/auth/login')) {
      clearStoredTokens();
      window.dispatchEvent(new Event('auth-expired'));
    }
  }

  if (!response.ok) {
    let errorDetail = `Error ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = await response.text() || response.statusText;
    }
    throw new Error(errorDetail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  async login(email, password) {
    const data = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
    setStoredTokens(data.access_token, data.refresh_token);
    return data;
  },
  async logout() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) await request('/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }) }, false);
    clearStoredTokens();
  },
  async getSessions() { return request('/auth/sessions'); },
  async logoutAllSessions() { await request('/auth/sessions', { method: 'DELETE' }, false); clearStoredTokens(); },
  async register({ email, password, nickname, fullname }) {
    return request('/auth/register', { method: 'POST', body: JSON.stringify({
      email, password, nickname: nickname || email.split('@')[0], fullname: fullname || nickname || email.split('@')[0],
    }) });
  },
  async getMe() { const user = await request('/users/me'); localStorage.setItem('user_info', JSON.stringify(user)); return user; },
  async getConversations(page = 1, size = 50, status = null) {
    let query = `?page=${page}&size=${size}`;
    if (status) query += `&status=${status}`;
    return request(`/conversations/${query}`);
  },
  async getOperatorQueue() { return request('/operator/queue'); },
  async assignConversation(id) { return request(`/operator/assign/${id}`, { method: 'POST' }); },
  async replyAsOperator(id, message) {
    return request(`/operator/reply/${id}`, { method: 'POST', body: JSON.stringify({ message }) });
  },
  async closeAsOperator(id) { return request(`/operator/close/${id}`, { method: 'POST' }); },
  async backToAi(id) { return request(`/operator/back_to_ai/${id}`, { method: 'POST' }); },
  async createConversation(priority = 'medium', channel = 'web') {
    return request('/conversations/', { method: 'POST', body: JSON.stringify({ priority, channel }) });
  },
  async getConversation(id) { return request(`/conversations/${id}`); },
  async closeConversation(id) { return request(`/conversations/${id}/close`, { method: 'POST' }); },
  async getMessages(id) { return request(`/conversations/${id}/messages`); },
  async sendMessage(id, content) {
    return request(`/conversations/${id}/messages`, { method: 'POST', body: JSON.stringify({ content }) });
  },
  async checkHealth() { return request('/health'); },
};
