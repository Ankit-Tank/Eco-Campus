import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Award,
  CheckCircle,
  Clock,
  Droplet,
  PowerOff,
  RefreshCw,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getGhostCurrent } from '../../services/ghostLoadApi.js'
import { getWaterAlerts } from '../../services/waterApi.js'
import { getActions, getSavingsRecords, getSavingsSummary } from '../../services/savingsApi.js'
import { formatNumber } from '../../utils/format.js'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'

const STATUS_BADGE = {
  VERIFIED: { bg: '#ecfdf5', text: '#059669', border: '#a7f3d0' },
  PENDING: { bg: '#fffbeb', text: '#d97706', border: '#fde68a' },
  PARTIAL: { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
  NOT_VERIFIED: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
}

export default function AdminAlerts() {
  const { t } = useLanguage()
  const [ghostCurrent, setGhostCurrent] = useState(null)
  const [waterAlerts, setWaterAlerts] = useState([])
  const [actions, setActions] = useState([])
  const [savingsRecords, setSavingsRecords] = useState([])
  const [savingsSummary, setSavingsSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function loadData() {
    setError(null)
    try {
      const [ghostRes, waterRes, actionsRes, recordsRes, summaryRes] = await Promise.all([
        getGhostCurrent(),
        getWaterAlerts(),
        getActions({ limit: 50 }),
        getSavingsRecords({ limit: 50 }),
        getSavingsSummary(),
      ])
      setGhostCurrent(ghostRes)
      setWaterAlerts((waterRes.alerts || []).filter((a) => a.status === 'SUSPECTED' || a.status === 'CONFIRMED'))
      setActions(actionsRes.actions || [])
      setSavingsRecords(recordsRes.records || [])
      setSavingsSummary(summaryRes)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const timer = setInterval(loadData, 10000)
    return () => clearInterval(timer)
  }, [])

  const activeGhostAlerts = (ghostCurrent?.rooms || []).filter((r) => r.is_alerting || r.ghost_kw > 0.5)

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('adminNav.alerts')} & Savings Verification Engine</h1>
          <p>Real-time waste detection alarms and closed-loop post-action verification ledger.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <button type="button" className="btn btn--outline" onClick={loadData}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </header>

      {error && <ErrorState error={error} onRetry={loadData} />}

      {loading && !savingsSummary && (
        <div aria-busy="true">
          <Skeleton height={100} radius={14} />
          <Skeleton height={320} radius={14} style={{ marginTop: 20 }} />
        </div>
      )}

      {savingsSummary && (
        <>
          <section className="kpi-strip">
            <div className="kpi">
              <p className="kpi-label">Verified Energy Conserved</p>
              <div className="kpi-value" style={{ color: '#059669' }}>
                <strong>{formatNumber(savingsSummary.total_kwh_reduced, 1)} kWh</strong>
              </div>
              <p className="kpi-note">{savingsSummary.total_records} verified intervals recorded</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Financial Savings Realized</p>
              <div className="kpi-value" style={{ color: '#059669' }}>
                <strong>₹{formatNumber(savingsSummary.total_rupees_saved, 2)}</strong>
              </div>
              <p className="kpi-note">Based on ₹8.50/kWh commercial tariff</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Carbon Emissions Avoided</p>
              <div className="kpi-value">
                <strong>{formatNumber(savingsSummary.total_co2_kg, 1)} kg</strong>
              </div>
              <p className="kpi-note">0.71 kg CO₂ / kWh regional grid factor</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Equivalent Fan-Hours</p>
              <div className="kpi-value">
                <strong>{formatNumber(savingsSummary.fan_equivalents, 0)} fans</strong>
              </div>
              <p className="kpi-note">Standard 75W ceiling fan equivalence</p>
            </div>
          </section>

          {/* Active Alarms Grid */}
          <div className="grid-2" style={{ marginTop: 24, gap: 20 }}>
            {/* Ghost Load Active Alerts */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Active Ghost Load Alarms</h2>
                  <p className="card-sub">Rooms exceeding baseline for 2+ consecutive 15-min intervals.</p>
                </div>
                <Zap size={20} color="#dc2626" />
              </div>

              {activeGhostAlerts.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: '#059669' }}>
                  <CheckCircle size={32} style={{ margin: '0 auto 8px' }} />
                  <p>All rooms within academic expected baseline.</p>
                </div>
              ) : (
                <ul className="report-list">
                  {activeGhostAlerts.map((r) => (
                    <li key={r.room_id} className="report-row" style={{ alignItems: 'flex-start' }}>
                      <div className="report-text" style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong>{r.room_code} - {r.room_name}</strong>
                          <span style={{ color: '#dc2626', fontWeight: 700 }}>+{formatNumber(r.ghost_kw, 2)} kW</span>
                        </div>
                        <div style={{ fontSize: 13, color: '#6b7280', marginTop: 4 }}>
                          Cause: <span style={{ color: '#b91c1c', fontWeight: 600 }}>{r.reason_code || r.dominant_reason_code || 'UNSCHEDULED_LOAD'}</span>
                        </div>
                        <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>
                          Actual: {formatNumber(r.actual_kw, 1)} kW | Expected: {formatNumber(r.expected_kw, 1)} kW
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Water Leak Alerts */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Water Anomaly Alerts</h2>
                  <p className="card-sub">Flagged nocturnal flow spikes across monitored plumbing.</p>
                </div>
                <Droplet size={20} color="#0f8fa0" />
              </div>

              {waterAlerts.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: '#059669' }}>
                  <CheckCircle size={32} style={{ margin: '0 auto 8px' }} />
                  <p>No open water leakage alarms.</p>
                </div>
              ) : (
                <ul className="report-list">
                  {waterAlerts.map((w) => (
                    <li key={w.id} className="report-row">
                      <div className="report-text" style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <strong>#{w.id} · {w.location_name}</strong>
                          <span style={{ color: '#ea580c', fontWeight: 700 }}>{w.status}</span>
                        </div>
                        <div style={{ fontSize: 13, color: '#4b5563', marginTop: 4 }}>
                          Flow: <strong>{formatNumber(w.avg_flow_lph, 1)} L/h</strong> (Baseline: {w.baseline_lph} L/h)
                        </div>
                        <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>
                          Est. Loss: {formatNumber(w.excess_litres, 0)} L (~{Math.round(w.bucket_equivalents)} buckets)
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {/* Corrective Actions & Verification Ledger */}
          <section className="card" style={{ marginTop: 24 }}>
            <div className="card-head">
              <div>
                <h2>Closed-Loop Switch-Off Verification Ledger</h2>
                <p className="card-sub">Tracking physical actions through post-event metering intervals to guarantee genuine energy savings.</p>
              </div>
              <ShieldCheck size={20} color="#059669" />
            </div>

            {actions.length === 0 ? (
              <p className="empty-text" style={{ padding: 24 }}>No switch-off actions recorded yet.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#6b7280', fontSize: 13 }}>
                      <th style={{ padding: '10px 12px' }}>Action ID</th>
                      <th style={{ padding: '10px 12px' }}>Location</th>
                      <th style={{ padding: '10px 12px' }}>Equipment</th>
                      <th style={{ padding: '10px 12px' }}>Logged By</th>
                      <th style={{ padding: '10px 12px' }}>Claimed Saving</th>
                      <th style={{ padding: '10px 12px' }}>Status</th>
                      <th style={{ padding: '10px 12px' }}>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {actions.map((act) => {
                      const st = act.verification_status || act.status || 'PENDING'
                      const style = STATUS_BADGE[st] || STATUS_BADGE.PENDING
                      return (
                        <tr key={act.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                          <td style={{ padding: '12px' }}><strong>ACT-{act.id}</strong></td>
                          <td style={{ padding: '12px' }}>
                            <strong>{act.room_code}</strong>
                          </td>
                          <td style={{ padding: '12px', textTransform: 'capitalize' }}>
                            {act.equipment}
                          </td>
                          <td style={{ padding: '12px', fontSize: 13 }}>
                            {act.user_email || 'Operator'}
                          </td>
                          <td style={{ padding: '12px', fontWeight: 600 }}>
                            {formatNumber(act.claimed_kwh, 2)} kWh
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span
                              className="chip"
                              style={{
                                fontSize: 11,
                                padding: '3px 8px',
                                background: style.bg,
                                color: style.text,
                                borderColor: style.border,
                                fontWeight: 600,
                              }}
                            >
                              {st}
                            </span>
                          </td>
                          <td style={{ padding: '12px', fontSize: 13, color: '#64748b' }}>
                            {act.notes || '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </>
  )
}
