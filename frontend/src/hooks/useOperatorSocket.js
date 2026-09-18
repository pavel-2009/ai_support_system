import { useEffect, useState } from 'react';

export function useOperatorSocket(accessToken, onEvent) {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!accessToken) return undefined;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${window.location.host}/api/operator/ws`, ['bearer', accessToken]);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try { onEvent(JSON.parse(event.data)); } catch { onEvent({ type: 'notification' }); }
    };
    return () => socket.close();
  }, [accessToken, onEvent]);

  return connected;
}
