import { useEffect, useRef, useState } from 'react';

export function useOperatorSocket(accessToken, onEvent) {
  const [connected, setConnected] = useState(false);
  const retryTimerRef = useRef(null);

  useEffect(() => {
    if (!accessToken) return undefined;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let disposed = false;
    let socket;
    const connect = () => {
      socket = new WebSocket(`${protocol}://${window.location.host}/api/operator/ws`, ['bearer', accessToken]);
      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        if (!disposed) retryTimerRef.current = window.setTimeout(connect, 3000);
      };
      socket.onmessage = (event) => {
        try { onEvent(JSON.parse(event.data)); } catch { onEvent({ type: 'notification' }); }
      };
    };
    connect();
    return () => {
      disposed = true;
      window.clearTimeout(retryTimerRef.current);
      socket?.close();
    };
  }, [accessToken, onEvent]);

  return connected;
}
