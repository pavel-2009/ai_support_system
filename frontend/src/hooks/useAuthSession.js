import { useEffect, useState } from 'react';
import { api, clearStoredTokens, getStoredToken } from '../services/api';

export default function useAuthSession() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      if (!getStoredToken()) {
        setAuthLoading(false);
        return;
      }

      try {
        setCurrentUser(await api.getMe());
      } catch {
        clearStoredTokens();
        setCurrentUser(null);
      } finally {
        setAuthLoading(false);
      }
    };

    restoreSession();
    const handleAuthExpired = () => setCurrentUser(null);
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, []);

  return { currentUser, authLoading, setCurrentUser };
}
