const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export const getStoredToken = () => {
  return localStorage.getItem('access_token');
};

export const setStoredTokens = (accessToken, refreshToken) => {
  if (accessToken) localStorage.setItem('access_token', accessToken);
  if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
};

export const clearStoredTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_info');
};

async function request(endpoint, options = {}) {
  const token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized, clear token if it wasn't a login attempt
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

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  // Auth
  async login(email, password) {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setStoredTokens(data.access_token, data.refresh_token);
    return data;
  },

  async register({ email, password, nickname, fullname }) {
    return await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        nickname: nickname || email.split('@')[0],
        fullname: fullname || nickname || email.split('@')[0],
      }),
    });
  },

  async getMe() {
    const user = await request('/users/me');
    localStorage.setItem('user_info', JSON.stringify(user));
    return user;
  },

  // Conversations
  async getConversations(page = 1, size = 50, status = null) {
    let query = `?page=${page}&size=${size}`;
    if (status) query += `&status=${status}`;
    return await request(`/conversations/${query}`);
  },

  async createConversation(priority = 'medium', channel = 'web') {
    return await request('/conversations/', {
      method: 'POST',
      body: JSON.stringify({ priority, channel }),
    });
  },

  async getConversation(id) {
    return await request(`/conversations/${id}`);
  },

  async closeConversation(id) {
    return await request(`/conversations/${id}/close`, {
      method: 'POST',
    });
  },

  // Messages
  async getMessages(conversationId) {
    return await request(`/conversations/${conversationId}/messages`);
  },

  async sendMessage(conversationId, content) {
    return await request(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },

  // System Health
  async checkHealth() {
    return await request('/health');
  }
};
