import { useCallback, useMemo, useState } from 'react';
import { createApiClient } from '../api/client';

const ACCESS_TOKEN = 'support_access_token';
const REFRESH_TOKEN = 'support_refresh_token';

export function useAuth() {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN));
  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN);
    localStorage.removeItem(REFRESH_TOKEN);
    setAccessToken(null);
  }, []);
  const api = useMemo(() => createApiClient({ getAccessToken: () => accessToken, onUnauthorized: logout }), [accessToken, logout]);
  const login = useCallback(async (email, password) => {
    const session = await api.login(email, password);
    localStorage.setItem(ACCESS_TOKEN, session.access_token);
    localStorage.setItem(REFRESH_TOKEN, session.refresh_token);
    setAccessToken(session.access_token);
  }, [api]);

  return { api, accessToken, login, logout };
}
