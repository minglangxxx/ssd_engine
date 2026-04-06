import { useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (url: string, onMessage: (data: unknown) => void) => {
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    const ws = new WebSocket(url);
    ws.onmessage = (event) => {
      try {
        onMessageRef.current(JSON.parse(event.data));
      } catch {
        onMessageRef.current(event.data);
      }
    };
    wsRef.current = ws;
    return () => ws.close();
  }, [url]);

  const send = useCallback((data: unknown) => {
    wsRef.current?.send(JSON.stringify(data));
  }, []);

  return { send };
};
