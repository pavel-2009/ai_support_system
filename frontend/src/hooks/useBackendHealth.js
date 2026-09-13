import { useEffect, useState } from 'react';
import { api } from '../services/api';

export default function useBackendHealth() {
  const [backendOnline, setBackendOnline] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.checkHealth();
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }
    };

    checkHealth();
    const intervalId = window.setInterval(checkHealth, 30_000);
    return () => window.clearInterval(intervalId);
  }, []);

  return backendOnline;
}
