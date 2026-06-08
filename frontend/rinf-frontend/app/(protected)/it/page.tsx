'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiRequest } from '@/lib/api';
import NotificationPanel from '@/components/NotificationPanel';
import { useAutoRefresh } from '@/hooks/useAutoRefresh';

interface OnboardingRequest {
  id: string;
  employee_name: string;
  role: string;
  start_date: string;
  hardware_tier: string;
  status: string;
}

interface PendingItem {
  onboarding_request: OnboardingRequest;
  existing_provision: unknown;
}

interface ProvisionForm {
  company_email: string;
  account_credentials: string;
  laptop_config: string;
}

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.25rem',
  fontSize: '0.85rem',
  fontWeight: 500,
  color: '#374151',
};

const inputStyle: React.CSSProperties = {
  padding: '0.4rem 0.6rem',
  border: '1px solid #d1d5db',
  borderRadius: '6px',
  fontSize: '0.875rem',
  outline: 'none',
};

const btnPrimary: React.CSSProperties = {
  padding: '0.4rem 0.9rem',
  background: '#2563eb',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '0.85rem',
  fontWeight: 500,
};

const btnReject: React.CSSProperties = {
  padding: '0.4rem 0.9rem',
  background: '#ef4444',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '0.85rem',
  fontWeight: 500,
};

const btnRefresh: React.CSSProperties = {
  marginBottom: '1.2rem',
  fontSize: '1.4rem',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
};

export default function ITPage() {
  const { token, user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [pending, setPending] = useState<PendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [provisionForms, setProvisionForms] = useState<
    Record<string, ProvisionForm>
  >({});
  const [rejectReason, setRejectReason] = useState<
    Record<string, string>
  >({});

  useEffect(() => {
    if (authLoading) return;

    if (!token || user?.role !== 'it') {
      router.push('/');
      return;
    }

    loadPending();
  }, [authLoading, token, user]);

  const loadPending = useCallback(async () => {
    setLoading(true);

    try {
      const data = await apiRequest<PendingItem[]>(
        '/it/pending',
        {},
        token
      );
      setPending(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useAutoRefresh({
    wsUrl: `${process.env.NEXT_PUBLIC_WS_URL}/ws`,
    onRefresh: loadPending,
  });

  const getForm = (id: string): ProvisionForm =>
    provisionForms[id] || {
      company_email: '',
      account_credentials: '',
      laptop_config: '',
    };

  const setField = (
    id: string,
    field: keyof ProvisionForm,
    value: string
  ) => {
    setProvisionForms(prev => ({
      ...prev,
      [id]: {
        ...getForm(id),
        [field]: value,
      },
    }));
  };

  const handleComplete = async (id: string) => {
    const form = getForm(id);

    if (
      !form.company_email ||
      !form.account_credentials ||
      !form.laptop_config
    ) {
      alert('All provisioning fields are required');
      return;
    }

    try {
      await apiRequest(
        `/it/provisions/${id}/complete`,
        {
          method: 'POST',
          body: JSON.stringify(form),
        },
        token
      );

      loadPending();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to complete');
    }
  };

  const handleReject = async (id: string) => {
    const reason = rejectReason[id];

    if (!reason) {
      alert('Rejection reason is required');
      return;
    }

    try {
      await apiRequest(
        `/it/provisions/${id}/reject`,
        {
          method: 'POST',
          body: JSON.stringify({ reason }),
        },
        token
      );

      loadPending();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to reject');
    }
  };

  if (authLoading || !user) {
    return <p style={{ padding: '2rem' }}>Loading…</p>;
  }

  return (
    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h1 style={{ marginTop: 0 }}>IT Panel</h1>

            <button onClick={loadPending} style={btnRefresh}>
              🔄
            </button>
          </div>
        <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
          Accounts and hardware to provision
        </p>

        {error && <p style={{ color: '#ef4444' }}>{error}</p>}

        {loading ? (
          <p>Loading…</p>
        ) : pending.length === 0 ? (
          <p style={{ color: '#9ca3af' }}>No pending provisioning.</p>
        ) : (
          pending.map(({ onboarding_request: req }) => {
            const form = getForm(req.id);

            return (
              <section
                key={req.id}
                style={{
                  background: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  padding: '1.25rem',
                  marginBottom: '1rem',
                }}
              >
                <p style={{ fontWeight: 600 }}>{req.employee_name}</p>
                <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                  {req.role} · starts {req.start_date} ·{' '}
                  <span style={{ fontWeight: 500 }}>
                    {req.hardware_tier}
                  </span>
                </p>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '0.75rem',
                  }}
                >
                  <label style={labelStyle}>
                    Company Email
                    <input
                      style={inputStyle}
                      value={form.company_email}
                      onChange={e =>
                        setField(req.id, 'company_email', e.target.value)
                      }
                    />
                  </label>

                  <label style={labelStyle}>
                    Account Credentials
                    <input
                      style={inputStyle}
                      value={form.account_credentials}
                      onChange={e =>
                        setField(req.id, 'account_credentials', e.target.value)
                      }
                    />
                  </label>

                  <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>
                    Laptop Config
                    <input
                      style={inputStyle}
                      value={form.laptop_config}
                      onChange={e =>
                        setField(req.id, 'laptop_config', e.target.value)
                      }
                    />
                  </label>
                </div>

                <div
                  style={{
                    display: 'flex',
                    gap: '0.75rem',
                    marginTop: '1rem',
                    alignItems: 'center',
                  }}
                >
                  <button
                    style={btnPrimary}
                    onClick={() => handleComplete(req.id)}
                  >
                    ✓ Mark Complete
                  </button>

                  <input
                    style={{ ...inputStyle, flex: 1 }}
                    placeholder="Rejection reason…"
                    value={rejectReason[req.id] || ''}
                    onChange={e =>
                      setRejectReason(r => ({
                        ...r,
                        [req.id]: e.target.value,
                      }))
                    }
                  />

                  <button
                    style={btnReject}
                    onClick={() => handleReject(req.id)}
                  >
                    ✗ Reject
                  </button>
                </div>
              </section>
            );
          })
        )}
      </div>

      {token && <NotificationPanel token={token} />}
    </div>
  );
}