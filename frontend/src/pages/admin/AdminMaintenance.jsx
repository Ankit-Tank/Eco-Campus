import { useEffect, useState } from 'react'
import {
  AlertCircle,
  Bell,
  CheckCircle,
  Clock,
  ExternalLink,
  Eye,
  Filter,
  Loader2,
  RefreshCw,
  UserCheck,
  Wrench,
} from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import {
  getAdminNotifications,
  getComplaints,
  patchComplaint,
} from '../../services/complaintsApi.js'
import { formatDate } from '../../utils/format.js'
import StatusBadge from '../../components/ui/StatusBadge.jsx'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'

export default function AdminMaintenance() {
  const { t, language } = useLanguage()
  const [statusFilter, setStatusFilter] = useState('all')
  const [complaints, setComplaints] = useState([])
  const [notifications, setNotifications] = useState([])
  const [overdueCount, setOverdueCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Selected complaint detail modal
  const [selected, setSelected] = useState(null)
  const [patchStatus, setPatchStatus] = useState('')
  const [patchNotes, setPatchNotes] = useState('')
  const [savingPatch, setSavingPatch] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')

  async function loadData() {
    setError(null)
    try {
      const [compRes, notifRes] = await Promise.all([
        getComplaints({ status: statusFilter === 'all' ? undefined : statusFilter }),
        getAdminNotifications(),
      ])
      setComplaints(compRes.complaints || [])
      setOverdueCount(compRes.overdue_count || 0)
      setNotifications(notifRes.notifications || [])
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [statusFilter])

  function openDetail(c) {
    setSelected(c)
    setPatchStatus(c.status)
    setPatchNotes(c.resolution_notes || '')
    setSuccessMsg('')
  }

  async function handleUpdateComplaint(e) {
    e.preventDefault()
    if (!selected) return
    setSavingPatch(true)
    try {
      await patchComplaint(selected.id, {
        status: patchStatus,
        admin_notes: patchNotes,
      })
      setSuccessMsg(`Complaint ${selected.complaint_code} updated to ${patchStatus}!`)
      setSelected(null)
      await loadData()
    } catch (err) {
      alert(err.message || 'Failed to update complaint')
    } finally {
      setSavingPatch(false)
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('adminNav.maintenance')} & Student Issue Triage</h1>
          <p>Review student reports of leaks, open taps, and electrical damage with photo evidence.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <label className="select-pill">
            <span className="visually-hidden">Status Filter</span>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">All Statuses</option>
              <option value="submitted">Submitted</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="assigned">Assigned</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="reopened">Reopened</option>
            </select>
          </label>

          <button type="button" className="btn btn--outline" onClick={loadData}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </header>

      {successMsg && (
        <div className="state-box" style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#065f46', marginBottom: 20 }}>
          <CheckCircle size={22} color="#059669" />
          <div>
            <strong>Status Updated</strong>
            <p>{successMsg}</p>
          </div>
        </div>
      )}

      {error && <ErrorState error={error} onRetry={loadData} />}

      {/* Admin Notifications Banner */}
      {notifications.length > 0 && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, padding: '12px 16px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
          <Bell size={20} color="#d97706" />
          <div style={{ flex: 1, fontSize: 13, color: '#92400e' }}>
            <strong>{notifications.length} recent system notifications:</strong> Latest: "{notifications[0].title} — {notifications[0].message}"
          </div>
        </div>
      )}

      {loading && !complaints.length && (
        <div aria-busy="true">
          <Skeleton height={380} radius={14} />
        </div>
      )}

      {!loading && (
        <section className="card">
          <div className="card-head">
            <div>
              <h2>Complaints Queue ({complaints.length})</h2>
              <p className="card-sub">
                {overdueCount > 0 ? (
                  <span style={{ color: '#dc2626', fontWeight: 600 }}>⚠ {overdueCount} issues overdue (&gt;48 hours)</span>
                ) : (
                  'All assigned maintenance items on schedule'
                )}
              </p>
            </div>
            <Wrench size={20} color="#4b5563" />
          </div>

          {complaints.length === 0 ? (
            <p className="empty-text" style={{ padding: 24 }}>No complaints match the selected filter.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#6b7280', fontSize: 13 }}>
                    <th style={{ padding: '10px 12px' }}>Code</th>
                    <th style={{ padding: '10px 12px' }}>Category & Title</th>
                    <th style={{ padding: '10px 12px' }}>Location</th>
                    <th style={{ padding: '10px 12px' }}>Reporter</th>
                    <th style={{ padding: '10px 12px' }}>Status</th>
                    <th style={{ padding: '10px 12px' }}>Reported At</th>
                    <th style={{ padding: '10px 12px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {complaints.map((c) => (
                    <tr key={c.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '12px' }}>
                        <strong>{c.complaint_code}</strong>
                        {c.is_overdue && (
                          <div style={{ fontSize: 11, color: '#dc2626', fontWeight: 700 }}>OVERDUE</div>
                        )}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div style={{ fontWeight: 600, color: '#1e293b' }}>{c.title || c.description}</div>
                        <div style={{ fontSize: 12, color: '#64748b', textTransform: 'capitalize' }}>
                          {c.category?.replace('_', ' ')}
                        </div>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <strong>{c.building}</strong>
                        <div style={{ fontSize: 12, color: '#64748b' }}>{c.location_detail}</div>
                      </td>
                      <td style={{ padding: '12px', fontSize: 13, color: '#4b5563' }}>
                        {c.student_email || 'Student'}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <StatusBadge status={c.status} />
                      </td>
                      <td style={{ padding: '12px', fontSize: 13, color: '#64748b' }}>
                        {formatDate(c.created_at, language)}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <button
                          type="button"
                          className="btn btn--outline"
                          style={{ padding: '6px 12px', fontSize: 13 }}
                          onClick={() => openDetail(c)}
                        >
                          <Eye size={14} /> Review
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Detail & Lifecycle Modal */}
      {selected && (
        <div className="scrim" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="card" style={{ maxWidth: 640, width: '92%', maxHeight: '88vh', overflowY: 'auto' }}>
            <div className="card-head">
              <h2>{selected.complaint_code} — Ticket Review</h2>
              <button type="button" className="icon-btn" onClick={() => setSelected(null)}>✕</button>
            </div>

            <div style={{ marginTop: 14 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
                <StatusBadge status={selected.status} />
                <span style={{ fontSize: 13, color: '#64748b' }}>Reported by: <strong>{selected.student_email}</strong></span>
              </div>

              <div style={{ padding: '12px 16px', background: '#f8fafc', borderRadius: 8, marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: '#64748b' }}>Location: <strong>{selected.building} · {selected.location_detail}</strong></div>
                <div style={{ fontSize: 14, color: '#1e293b', marginTop: 8, fontWeight: 500 }}>
                  "{selected.description}"
                </div>
              </div>

              {selected.image_url && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>Photo Evidence:</div>
                  <img
                    src={selected.image_url}
                    alt="Complaint evidence"
                    style={{ maxWidth: '100%', maxHeight: 240, borderRadius: 8, objectFit: 'cover', border: '1px solid #e2e8f0' }}
                  />
                </div>
              )}

              {/* Audit History Timeline */}
              {selected.history && selected.history.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h4 style={{ fontSize: 13, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>Audit History</h4>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {selected.history.map((h) => (
                      <li key={h.id} style={{ fontSize: 12, padding: '4px 0', borderBottom: '1px dashed #e2e8f0', color: '#4b5563' }}>
                        <strong>{h.new_status}</strong>: {h.note} <span style={{ color: '#94a3b8' }}>({h.changed_at ? h.changed_at.slice(0, 16).replace('T', ' ') : ''})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Lifecycle Update Form */}
              <form onSubmit={handleUpdateComplaint} style={{ borderTop: '1px solid #e2e8f0', paddingTop: 14 }}>
                <div className="field">
                  <label htmlFor="patch-status">Update Lifecycle Status</label>
                  <div className="select-field">
                    <select
                      id="patch-status"
                      value={patchStatus}
                      onChange={(e) => setPatchStatus(e.target.value)}
                    >
                      <option value="submitted">Submitted</option>
                      <option value="acknowledged">Acknowledged (Noticed by facility)</option>
                      <option value="assigned">Assigned (Dispatched to technician)</option>
                      <option value="in_progress">In Progress (Work ongoing)</option>
                      <option value="resolved">Resolved (Fix verified)</option>
                      <option value="reopened">Reopened (Issue reoccurred)</option>
                    </select>
                  </div>
                </div>

                <div className="field" style={{ marginTop: 12 }}>
                  <label htmlFor="patch-notes">Resolution Notes / Action Taken</label>
                  <textarea
                    id="patch-notes"
                    rows={2}
                    value={patchNotes}
                    onChange={(e) => setPatchNotes(e.target.value)}
                    placeholder="e.g. Technician replaced leaking valve. Water supply restored."
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
                  <button type="button" className="btn btn--outline" onClick={() => setSelected(null)}>Close</button>
                  <button type="submit" className="btn btn--primary" disabled={savingPatch}>
                    {savingPatch ? <Loader2 size={16} className="spin" /> : 'Update Status'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
