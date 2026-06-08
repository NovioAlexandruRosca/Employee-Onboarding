'use client';
import { useEffect } from 'react';

type Options = {
  onRefresh: () => void;
  wsUrl: string;
};

export function useAutoRefresh({ onRefresh, wsUrl }: Options) {
  useEffect(() => {
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type) {
          onRefresh();
        }
      } catch {
      }
    };

    ws.onerror = () => {
      console.warn('WebSocket error');
    };

    return () => ws.close();
  }, [wsUrl]);
}