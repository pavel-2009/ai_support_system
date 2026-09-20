const API_PREFIX = '/api';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export function createApiClient({ getAccessToken, onUnauthorized }) {
  async function request(path, options = {}) {
    const token = getAccessToken();
    const response = await fetch(`${API_PREFIX}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    if (response.status === 401) onUnauthorized?.();
    if (response.status === 204) return null;

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiError(payload?.detail || 'Сервис временно недоступен.', response.status);
    }
    return payload;
  }

  return {
    login: (email, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
    currentUser: () => request('/users/me'),
    conversations: ({ operatorId, status } = {}) => {
      const params = new URLSearchParams({ size: '100' });
      if (operatorId != null) params.set('operator_id', String(operatorId));
      if (status) params.set('status', status);
      return request(`/conversations/?${params.toString()}`);
    },
    createConversation: () => request('/conversations/', { method: 'POST', body: JSON.stringify({ priority: 'medium', channel: 'web' }) }),
    messages: (conversationId) => request(`/conversations/${conversationId}/messages`),
    sendMessage: (conversationId, content) => request(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ content }),
    }),
    queue: () => request('/operator/queue'),
    assign: (conversationId) => request(`/operator/assign/${conversationId}`, { method: 'POST' }),
    operatorReply: (conversationId, message) => request(`/operator/reply/${conversationId}`, { method: 'POST', body: JSON.stringify({ message }) }),
    close: (conversationId) => request(`/operator/close/${conversationId}`, { method: 'POST' }),
    backToAi: (conversationId) => request(`/operator/back_to_ai/${conversationId}`, { method: 'POST' }),
    users: () => request('/users/'),
  };
}
