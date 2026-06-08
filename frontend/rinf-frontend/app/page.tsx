'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiRequest } from '@/lib/api';

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
    role: string;
  };
}

const inputStyle: React.CSSProperties = {
  padding: '0.5rem 0.6rem',
  border: '1px solid #d1d5db',
  borderRadius: '16px',
  fontSize: '0.875rem',
  outline: 'none',
  width: '100%',
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.25rem',
  fontSize: '0.85rem',
  fontWeight: 500,
  color: '#374151',
};

const btnPrimary: React.CSSProperties = {
  padding: '0.5rem 0.9rem',
  background: '#032a0a',
  color: '#fff',
  border: 'none',
  borderRadius: '16px',
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: 500,
};

const btnSecondary: React.CSSProperties = {
  padding: '0.4rem 0.7rem',
  background: '#f3f4f6',
  border: '1px solid #d1d5db',
  borderRadius: '16px',
  cursor: 'pointer',
  fontSize: '0.85rem',
  color: '#374151',
};

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [loginForm, setLoginForm] = useState({
    username: '',
    password: '',
  });

  const [regForm, setRegForm] = useState({
    username: '',
    email: '',
    password: '',
    role: 'hr',
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const data = await apiRequest<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm),
      });

      login(data.access_token, data.user);
      const roleRoutes: Record<string, string> = {
        hr: '/hr',
        manager: '/manager',
        finance: '/finance',
        it: '/it',
      };

      router.push(roleRoutes[data.user.role] || '/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify(regForm),
      });

      setSuccess('Account created. You can now log in.');
      setMode('login');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#f9fafb',
      }}
    >
      <div
        style={{
          width: '420px',
          background: '#fff',
          border: '1px solid #e5e7eb',
          borderRadius: '10px',
          padding: '1.5rem',
        }}
      >
        <h1 style={{ marginTop: 0 }}>RINF Onboarding</h1>

        {/* Switch between login and register */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <button
            style={mode === 'login' ? btnPrimary : btnSecondary}
            onClick={() => {
              setMode('login');
              setError('');
              setSuccess('');
            }}
          >
            Login
          </button>

          <button
            style={mode === 'register' ? btnPrimary : btnSecondary}
            onClick={() => {
              setMode('register');
              setError('');
              setSuccess('');
            }}
          >
            Register
          </button>
        </div>

        {error && (
          <p style={{ color: '#ef4444', fontSize: '0.85rem' }}>{error}</p>
        )}
        {success && (
          <p style={{ color: '#22c55e', fontSize: '0.85rem' }}>{success}</p>
        )}

        {mode === 'login' && (
          <form onSubmit={handleLogin} style={{ display: 'grid', gap: '0.75rem' }}>
            <label style={labelStyle}>
              Username
              <input
                style={inputStyle}
                value={loginForm.username}
                onChange={e =>
                  setLoginForm(f => ({ ...f, username: e.target.value }))
                }
              />
            </label>

            <label style={labelStyle}>
              Password
              <input
                style={inputStyle}
                type="password"
                value={loginForm.password}
                onChange={e =>
                  setLoginForm(f => ({ ...f, password: e.target.value }))
                }
              />
            </label>

            <button type="submit" style={btnPrimary}>
              Login
            </button>
          </form>
        )}

        {mode === 'register' && (
          <form onSubmit={handleRegister} style={{ display: 'grid', gap: '0.75rem' }}>
            <label style={labelStyle}>
              Username
              <input
                style={inputStyle}
                value={regForm.username}
                onChange={e =>
                  setRegForm(f => ({ ...f, username: e.target.value }))
                }
              />
            </label>

            <label style={labelStyle}>
              Email
              <input
                style={inputStyle}
                type="email"
                value={regForm.email}
                onChange={e =>
                  setRegForm(f => ({ ...f, email: e.target.value }))
                }
              />
            </label>

            <label style={labelStyle}>
              Password
              <input
                style={inputStyle}
                type="password"
                minLength={8}
                value={regForm.password}
                onChange={e =>
                  setRegForm(f => ({ ...f, password: e.target.value }))
                }
              />
            </label>

            <label style={labelStyle}>
              Role
              <select
                style={inputStyle}
                value={regForm.role}
                onChange={e =>
                  setRegForm(f => ({ ...f, role: e.target.value }))
                }
              >
                <option value="hr">HR</option>
                <option value="manager">Manager</option>
                <option value="finance">Finance</option>
                <option value="it">IT</option>
              </select>
            </label>

            <button type="submit" style={btnPrimary}>
              Create Account
            </button>
          </form>
        )}
      </div>
    </div>
  );
}