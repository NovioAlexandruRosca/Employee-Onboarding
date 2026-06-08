'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

const roleLabel: Record<string, string> = {
  hr: 'HR',
  manager: 'Manager',
  finance: 'Finance',
  it: 'IT',
};

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout, loading: authLoading } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  if (authLoading) return <p style={{ padding: '2rem' }}>Loading…</p>;
  if (!user) return <p style={{ padding: '2rem' }}>Unauthorized</p>;

  return (
    <div style={{ minHeight: '100vh', background: '#f3f4f6', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{
        background: '#fff',
        borderBottom: '1px solid #e5e7eb',
        padding: '0 1.5rem',
        height: '52px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <nav style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', fontSize: '0.9rem' }}>
          <span style={{ fontWeight: 700, color: '#111827', marginRight: '0.5rem' }}>RINF</span>
          {user.role === 'hr' && <Link href="/hr" style={navLink}>HR</Link>}
          {user.role === 'manager' && <Link href="/manager" style={navLink}>Manager</Link>}
          {user.role === 'finance' && <Link href="/finance" style={navLink}>Finance</Link>}
          {user.role === 'it' && <Link href="/it" style={navLink}>IT</Link>}
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.85rem' }}>
          <span style={{ color: '#6b7280' }}>
            <strong style={{ color: '#111827' }}>{user.username}</strong>
            {' '}·{' '}
            <span style={{
              background: '#eff6ff', color: '#2563eb',
              borderRadius: '999px', padding: '0.1rem 0.5rem', fontWeight: 600, fontSize: '0.78rem',
            }}>{roleLabel[user.role] ?? user.role}</span>
          </span>
          <button onClick={handleLogout} style={{
            padding: '0.3rem 0.8rem', background: '#f3f4f6',
            border: '1px solid #d1d5db', borderRadius: '6px',
            cursor: 'pointer', fontSize: '0.82rem', color: '#374151',
          }}>Logout</button>
        </div>
      </header>

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem' }}>
        {children}
      </main>
    </div>
  );
}

const navLink: React.CSSProperties = { color: '#374151', textDecoration: 'none', fontWeight: 500 };