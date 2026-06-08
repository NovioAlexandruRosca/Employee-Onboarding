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
  fisa_de_post: string;
  created_at: string;
  rejection_reason: string | null;
}

const statusColors: Record<string, string> = {
  manager_review: '#f59e0b',
  finance_review: '#3b82f6',
  it_provisioning: '#8b5cf6',
  completed: '#22c55e',
  needs_rework: '#ef4444',
};

const btnRefresh: React.CSSProperties = {
  marginTop: '0.25rem',
  fontSize: '1.2rem',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
};

export default function HRPage() {
  const { token, user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [requests, setRequests] = useState<OnboardingRequest[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const [createForm, setCreateForm] = useState({
    employee_name: '',
    role: '',
    start_date: '',
    hardware_tier: 'standard',
  });

  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    employee_name: '',
    role: '',
    start_date: '',
    hardware_tier: 'standard',
  });
  const [editError, setEditError] = useState('');

  useEffect(() => {
    if (authLoading) return;

    if (!token || user?.role !== 'hr') {
      router.push('/');
      return;
    }

    loadRequests();
  }, [authLoading, token, user]);

  const loadRequests = useCallback( async () => {
    setLoading(true);

    try {
      const data = await apiRequest<OnboardingRequest[]>(
        '/hr/onboarding',
        {},
        token
      );
      setRequests(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useAutoRefresh({
    wsUrl: `${process.env.NEXT_PUBLIC_WS_URL}/ws`,
    onRefresh: loadRequests,
  });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError('');
    setCreateSuccess('');

    try {
      await apiRequest(
        '/hr/onboarding',
        {
          method: 'POST',
          body: JSON.stringify(createForm),
        },
        token
      );

      setCreateSuccess('Onboarding request created.');
      setCreateForm({
        employee_name: '',
        role: '',
        start_date: '',
        hardware_tier: 'standard',
      });

      loadRequests();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create');
    }
  };

  const startEdit = (req: OnboardingRequest) => {
    setEditingId(req.id);
    setEditForm({
      employee_name: req.employee_name,
      role: req.role,
      start_date: req.start_date,
      hardware_tier: req.hardware_tier,
    });
    setEditError('');
  };

  const handleEdit = async (e: React.FormEvent, id: string) => {
    e.preventDefault();
    setEditError('');

    try {
      await apiRequest(
        `/hr/onboarding/${id}`,
        {
          method: 'PUT',
          body: JSON.stringify(editForm),
        },
        token
      );

      setEditingId(null);
      loadRequests();
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : 'Failed to save');
    }
  };

  const handleResubmit = async (id: string) => {
    try {
      await apiRequest(
        `/hr/onboarding/${id}/resubmit`,
        { method: 'POST' },
        token
      );

      loadRequests();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to resubmit');
    }
  };

  if (authLoading || !user) {
    return <p style={{ padding: '2rem' }}>Loading…</p>;
  }

  return (
    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <h1 style={{ marginTop: 0 }}>HR Panel</h1>

        <section
          style={{
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
          }}
        >
          <h2 style={{ marginTop: 0, fontSize: '1rem' }}>
            New Onboarding Request
          </h2>

          {createError && <p style={{ color: '#ef4444' }}>{createError}</p>}
          {createSuccess && (
            <p style={{ color: '#22c55e' }}>{createSuccess}</p>
          )}

          <form
            onSubmit={handleCreate}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '0.75rem',
            }}
          >
            <label>
              Employee Name
              <input
                value={createForm.employee_name}
                onChange={e =>
                  setCreateForm(f => ({
                    ...f,
                    employee_name: e.target.value,
                  }))
                }
                required
              />
            </label>

            <label>
              Role
              <input
                value={createForm.role}
                onChange={e =>
                  setCreateForm(f => ({ ...f, role: e.target.value }))
                }
                required
              />
            </label>

            <label>
              Start Date
              <input
                type="date"
                value={createForm.start_date}
                onChange={e =>
                  setCreateForm(f => ({
                    ...f,
                    start_date: e.target.value,
                  }))
                }
                required
              />
            </label>

            <label>
              Hardware Tier
              <select
                value={createForm.hardware_tier}
                onChange={e =>
                  setCreateForm(f => ({
                    ...f,
                    hardware_tier: e.target.value,
                  }))
                }
              >
                <option value="standard">Standard</option>
                <option value="premium">Premium</option>
              </select>
            </label>

            <div style={{ gridColumn: '1 / -1' }}>
              <button type="submit">Create Request</button>
            </div>
          </form>
        </section>

        <section
          style={{
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '1.25rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h2 style={{ marginTop: 0, marginBottom: 0 }}>
              My Requests
            </h2>

            <button onClick={loadRequests} style={btnRefresh}>
              🔄
            </button>
          </div>

          {error && <p style={{ color: '#ef4444' }}>{error}</p>}

          {loading ? (
            <p>Loading…</p>
          ) : requests.length === 0 ? (
            <p style={{ color: '#9ca3af' }}>No requests yet.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {[
                    'Employee',
                    'Role',
                    'Start Date',
                    'Hardware',
                    'Status',
                    'Rejection Reason',
                    'Actions',
                  ].map(h => (
                    <th key={h} style={{ textAlign: 'left' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {requests.map(req => (
                  <tr key={req.id}>
                    <td>{req.employee_name}</td>
                    <td>{req.role}</td>
                    <td>{req.start_date}</td>
                    <td>{req.hardware_tier}</td>
                    <td>
                      <span
                        style={{
                          color: statusColors[req.status] ?? '#6b7280',
                          fontWeight: 600,
                        }}
                      >
                        {req.status}
                      </span>
                    </td>
                    <td>{req.rejection_reason ?? '-'}</td>
                    <td>
                      {req.status === 'needs_rework' && (
                        <>
                          <button onClick={() => startEdit(req)}>
                            Edit
                          </button>{' '}
                          <button onClick={() => handleResubmit(req.id)}>
                            Resubmit
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {editingId && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: '#0006',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{ background: '#fff', padding: '1rem' }}>
              <h3>Edit Request</h3>

              {editError && <p style={{ color: '#ef4444' }}>{editError}</p>}

              <form onSubmit={e => handleEdit(e, editingId)}>
                <input
                  value={editForm.employee_name}
                  onChange={e =>
                    setEditForm(f => ({
                      ...f,
                      employee_name: e.target.value,
                    }))
                  }
                />

                <input
                  value={editForm.role}
                  onChange={e =>
                    setEditForm(f => ({ ...f, role: e.target.value }))
                  }
                />

                <input
                  type="date"
                  value={editForm.start_date}
                  onChange={e =>
                    setEditForm(f => ({
                      ...f,
                      start_date: e.target.value,
                    }))
                  }
                />

                <select
                  value={editForm.hardware_tier}
                  onChange={e =>
                    setEditForm(f => ({
                      ...f,
                      hardware_tier: e.target.value,
                    }))
                  }
                >
                  <option value="standard">Standard</option>
                  <option value="premium">Premium</option>
                </select>

                <button type="submit">Save</button>
                <button type="button" onClick={() => setEditingId(null)}>
                  Cancel
                </button>
              </form>
            </div>
          </div>
        )}
      </div>

      {token && <NotificationPanel token={token} />}
    </div>
  );
}