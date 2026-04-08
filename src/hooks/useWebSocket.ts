import { useEffect, useRef, useCallback, useState } from 'react';
import type { WSMessage, WSCommand } from '../types/parking';

const DEFAULT_WS_URL = 'ws://192.168.1.9:8765';
const RECONNECT_INTERVAL = 3000;
const MAX_RECONNECT_ATTEMPTS = 50;

interface UseWebSocketOptions {
  url?: string;
  onMessage: (message: WSMessage) => void;
  onStatusChange?: (connected: boolean) => void;
}

export function useWebSocket({ url, onMessage, onStatusChange }: UseWebSocketOptions) {
  const wsUrl = url || DEFAULT_WS_URL;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const [connected, setConnected] = useState(false);

  // Use refs to avoid stale closures and prevent unnecessary reconnections
  const onMessageRef = useRef(onMessage);
  const onStatusChangeRef = useRef(onStatusChange);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
  }, [onStatusChange]);

  const updateConnected = useCallback((status: boolean) => {
    setConnected(status);
    onStatusChangeRef.current?.(status);
  }, []);

  const connect = useCallback(() => {
    // Close existing connection first
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent triggering reconnect
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WS] Connected to', wsUrl);
        reconnectAttempts.current = 0;
        updateConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          onMessageRef.current(message);
        } catch (err) {
          console.error('[WS] Failed to parse message:', err);
        }
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected');
        updateConnected(false);
        // Schedule reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          reconnectTimerRef.current = setTimeout(() => {
            console.log(`[WS] Reconnecting... (attempt ${reconnectAttempts.current})`);
            connect();
          }, RECONNECT_INTERVAL);
        } else {
          console.log('[WS] Max reconnect attempts reached');
        }
      };

      ws.onerror = (err) => {
        console.error('[WS] Error:', err);
        ws.close();
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WS] Connection failed:', err);
    }
  }, [wsUrl, updateConnected]);

  const sendCommand = useCallback((command: WSCommand) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(command));
    } else {
      console.warn('[WS] Cannot send command: not connected');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent triggering reconnect
      wsRef.current.close();
      wsRef.current = null;
    }
    updateConnected(false);
  }, [updateConnected]);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { connected, sendCommand, disconnect, reconnect: connect };
}
