import { useCallback, useEffect, useRef, useState } from 'react';
import { getStoredToken } from '../services/api';

export default function useOperatorWebSocket({
  enabled = true,
  onEscalated,
  onOperatorAssigned,
  onMessageSent,
  onTyping,
  onConversationClosed,
  onConversationReturnedToAi,
} = {}) {
  const [wsStatus, setWsStatus] = useState('disconnected');
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const pingIntervalRef = useRef(null);

  // Keep latest callbacks in ref to avoid reconnecting on every callback change
  const callbacksRef = useRef({
    onEscalated,
    onOperatorAssigned,
    onMessageSent,
    onTyping,
    onConversationClosed,
    onConversationReturnedToAi,
  });

  useEffect(() => {
    callbacksRef.current = {
      onEscalated,
      onOperatorAssigned,
      onMessageSent,
      onTyping,
      onConversationClosed,
      onConversationReturnedToAi,
    };
  });

  const connect = useCallback(() => {
    if (!enabled) return;

    const token = getStoredToken();
    if (!token) {
      setWsStatus('disconnected');
      return;
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/operator/ws`;

      setWsStatus('connecting');

      // Pass bearer token via Sec-WebSocket-Protocol
      const socket = new WebSocket(wsUrl, ['bearer', token]);
      wsRef.current = socket;

      socket.onopen = () => {
        setWsStatus('connected');
        reconnectAttemptsRef.current = 0;

        // Periodic heartbeat
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type = data.type;

          if (type === 'conversation_escalated') {
            callbacksRef.current.onEscalated?.(data.conversation_id, data);
          } else if (type === 'operator_assigned') {
            callbacksRef.current.onOperatorAssigned?.(data);
          } else if (type === 'message_sent') {
            callbacksRef.current.onMessageSent?.(data);
          } else if (type === 'typing') {
            callbacksRef.current.onTyping?.(data);
          } else if (type === 'conversation_closed') {
            callbacksRef.current.onConversationClosed?.(data);
          } else if (type === 'conversation_returned_to_ai') {
            callbacksRef.current.onConversationReturnedToAi?.(data);
          }
        } catch (err) {
          console.warn('WS message parse error:', err);
        }
      };

      socket.onclose = () => {
        setWsStatus('disconnected');
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

        if (enabled) {
          const delay = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 15000);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setWsStatus('disconnected');
    }
  }, [enabled]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setWsStatus('disconnected');
    }

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, enabled]);

  const sendTyping = useCallback((conversationId, isTyping = true) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'typing',
          conversation_id: conversationId,
          is_typing: isTyping,
        }),
      );
    }
  }, []);

  return {
    wsStatus,
    sendTyping,
    reconnect: connect,
  };
}
