'use client';
import { useEffect, useRef, useState } from 'react';

interface Notification {
  id: number;
  message: string;
  timestamp: string;
}

export default function NotificationPanel({ token }: { token: string }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('connecting');
  const nextId = useRef(0);

  useEffect(() => {
    const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${WS_URL}/ws?token=${token}`);

    ws.onopen = () => setWsStatus('connected');
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data as string);
        if (data.event === 'connected') return;
        setNotifications(prev =>
          [{
            id: nextId.current++,
            message: data.message || JSON.stringify(data),
            timestamp: data.timestamp || new Date().toISOString(),
          }, ...prev].slice(0, 50)
        );
      } catch { 
          console.warn('Invalid notification:', e.data);
       }
    };
    ws.onclose = () => setWsStatus('disconnected');
    ws.onerror = () => setWsStatus('error');

    return () => ws.close();
  }, [token]);

  const dot: Record<string, string> = {
    connected: '#22c55e',
    connecting: '#f59e0b',
    disconnected: '#9ca3af',
    error: '#ef4444',
  };

  return (
    <aside style={{
      width: '280px',
      flexShrink: 0,
      background: '#f9fafb',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      padding: '1rem',
      alignSelf: 'flex-start',
      position: 'sticky',
      top: '1rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <span style={{
          width: '8px', height: '8px', borderRadius: '50%',
          background: dot[wsStatus], display: 'inline-block',
        }} />
        <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Live Notifications</h3>
      </div>
      {notifications.length === 0 ? (
        <p style={{ color: '#9ca3af', fontSize: '0.85rem', margin: 0 }}>No notifications yet.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {notifications.map(n => (
            <li key={n.id} style={{
              fontSize: '0.82rem',
              padding: '0.4rem 0',
              borderBottom: '1px solid #e5e7eb',
              color: '#374151',
            }}>
              <span style={{ color: '#9ca3af', marginRight: '0.4rem' }}>
                {new Date(n.timestamp).toLocaleTimeString()}
              </span>
              {n.message}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
