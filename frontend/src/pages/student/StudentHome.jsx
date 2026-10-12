import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Bell, Zap, Trophy, X, ArrowRight, CheckCircle2 } from 'lucide-react'
import StatsStrip from '../../components/student/StatsStrip.jsx'
import ReportForm from '../../components/student/ReportForm.jsx'
import RecentReports from '../../components/student/RecentReports.jsx'
import ImpactPanel from '../../components/student/ImpactPanel.jsx'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getUser } from '../../auth/session.js'
import { getStudentHome } from '../../services/dashboardApi.js'
import { reportApplianceLeftOn } from '../../services/reportsApi.js'
import { getRooms } from '../../services/roomsApi.js'

export default function StudentHome() {
  const { t } = useLanguage()
  const user = getUser()
  const { status, data, error, reload } = useApi(() => getStudentHome(user), [])

  const [showSignalModal, setShowSignalModal] = useState(false)
  const [rooms, setRooms] = useState([])
  const [signalRoom, setSignalRoom] = useState('')
  const [signalAppliance, setSignalAppliance] = useState('Air Conditioner')
  const [signalNotes, setSignalNotes] = useState('')
  const [submittingSignal, setSubmittingSignal] = useState(false)
  const [signalSuccess, setSignalSuccess] = useState('')
  const [signalError, setSignalError] = useState('')

  useEffect(() => {
    getRooms()
      .then((res) => {
        const list = Array.isArray(res) ? res : (res?.rooms || res?.items || [])
        setRooms(list)
        if (list.length > 0) setSignalRoom(list[0].room_code || list[0].id)
      })
      .catch(() => {})
  }, [])

  async function handleSendSignal(e) {
    e.preventDefault()
    if (!signalRoom) return
    setSubmittingSignal(true)
    setSignalError('')
    setSignalSuccess('')

    try {
      await reportApplianceLeftOn({
        roomId: signalRoom,
        equipmentType: signalAppliance,
        notes: signalNotes.trim() || undefined,
      })
      setSignalSuccess(`Signal sent for ${signalRoom}! Facility staff notified.`)
      setSignalNotes('')
      reload()
      setTimeout(() => {
        setShowSignalModal(false)
        setSignalSuccess('')
      }, 1600)
    } catch (err) {
      setSignalError(err?.message || 'Failed to submit signal. Please try again.')
    } finally {
      setSubmittingSignal(false)
    }
  }

  const name = data?.name || user?.name || ''

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('student.welcome', { name })}</h1>
          <p>{t('student.subtitle')}</p>
          {data?.is_simulated && <span className="sim-pill">{t('shell.simulated')}</span>}
        </div>
        <div className="toolbar" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn--outline"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, borderColor: '#f59e0b', color: '#b45309' }}
            onClick={() => setShowSignalModal(true)}
          >
            <Zap size={16} /> Signal Appliance Left On
          </button>
          <button type="button" className="icon-btn icon-btn--round" aria-label={t('shell.notifications')}>
            <Bell size={20} />
          </button>
          <span className="user-avatar user-avatar--lg" aria-hidden="true">
            {name.charAt(0).toUpperCase()}
          </span>
        </div>
      </header>

      {/* Campus Leaderboard Quick Banner */}
      <div
        className="card"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'linear-gradient(90deg, rgba(20,184,166,0.08) 0%, rgba(59,130,246,0.08) 100%)',
          borderLeft: '4px solid #0d9488',
          marginBottom: 20,
          padding: '14px 20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#ccfbf1', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0f766e' }}>
            <Trophy size={20} />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600 }}>Campus Energy Efficiency Challenge</h4>
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#475569' }}>See which campus blocks are minimizing ghost waste this week.</p>
          </div>
        </div>
        <Link to="/student/leaderboard" className="btn btn--primary" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', padding: '6px 14px' }}>
          View Leaderboard <ArrowRight size={14} />
        </Link>
      </div>

      {status === 'error' && <ErrorState error={error} onRetry={reload} />}

      {status === 'loading' && !data && (
        <div aria-busy="true">
          <Skeleton height={90} radius={14} />
          <div className="grid-student" style={{ marginTop: 20 }}>
            <Skeleton height={560} radius={14} />
            <Skeleton height={560} radius={14} />
          </div>
        </div>
      )}

      {data && (
        <>
          <StatsStrip stats={data.stats} />
          <div className="grid-student">
            <ReportForm onSubmitted={reload} />
            <div className="stack">
              <RecentReports reports={data.recent} />
              <ImpactPanel impact={data.impact} />
            </div>
          </div>
        </>
      )}

      {/* Quick Appliance Left On Signal Modal */}
      {showSignalModal && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="card modal-card" style={{ maxWidth: 480, width: '100%', position: 'relative' }}>
            <button
              type="button"
              className="icon-btn"
              onClick={() => setShowSignalModal(false)}
              style={{ position: 'absolute', top: 16, right: 16 }}
              aria-label="Close"
            >
              <X size={18} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#b45309' }}>
                <Zap size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Signal Appliance Left On</h3>
                <p style={{ margin: 0, fontSize: '0.82rem', color: '#64748b' }}>Immediately notifies facility managers to verify & turn it off</p>
              </div>
            </div>

            {signalSuccess ? (
              <div style={{ padding: '24px 0', textAlign: 'center' }}>
                <CheckCircle2 size={40} color="#16a34a" style={{ margin: '0 auto 12px' }} />
                <p style={{ fontWeight: 600, color: '#16a34a', margin: 0 }}>{signalSuccess}</p>
              </div>
            ) : (
              <form onSubmit={handleSendSignal} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {signalError && (
                  <p className="form-message form-message--error" role="alert" style={{ margin: 0 }}>
                    {signalError}
                  </p>
                )}

                <div className="field">
                  <label htmlFor="sig-room">Room / Location *</label>
                  <select
                    id="sig-room"
                    value={signalRoom}
                    onChange={(e) => setSignalRoom(e.target.value)}
                    required
                  >
                    {rooms.length > 0 ? (
                      rooms.map((r) => (
                        <option key={r.id} value={r.room_code || r.id}>
                          {r.room_code} — {r.name} ({r.block})
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="A-101">A-101 — Seminar Hall A (Block A)</option>
                        <option value="A-102">A-102 — Classroom 1 (Block A)</option>
                        <option value="B-201">B-201 — Computer Lab 1 (Block B)</option>
                        <option value="C-301">C-301 — Lecture Theatre C (Block C)</option>
                      </>
                    )}
                  </select>
                </div>

                <div className="field">
                  <label htmlFor="sig-type">Appliance Type *</label>
                  <select
                    id="sig-type"
                    value={signalAppliance}
                    onChange={(e) => setSignalAppliance(e.target.value)}
                  >
                    <option value="Air Conditioner">Air Conditioner (AC)</option>
                    <option value="Lights">Room Lights</option>
                    <option value="Fans">Ceiling Fans</option>
                    <option value="Computers">Lab Computers / Monitors</option>
                    <option value="Projector">AV Projector</option>
                    <option value="Other">Other Equipment</option>
                  </select>
                </div>

                <div className="field">
                  <label htmlFor="sig-notes">Observations / Details (Optional)</label>
                  <input
                    id="sig-notes"
                    type="text"
                    value={signalNotes}
                    onChange={(e) => setSignalNotes(e.target.value)}
                    placeholder="e.g. Empty locked room with cooling running"
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
                  <button
                    type="button"
                    className="btn btn--outline"
                    onClick={() => setShowSignalModal(false)}
                    disabled={submittingSignal}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={submittingSignal}
                  >
                    {submittingSignal ? 'Submitting...' : 'Send Signal'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  )
}

