import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  AlertCircle,
  CheckCircle,
  Droplet,
  FileText,
  Loader2,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import {
  getWaterAlerts,
  getWaterLocations,
  getWaterSeries,
  patchWaterAlert,
} from '../../services/waterApi.js'
import { formatNumber } from '../../utils/format.js'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'

export default function AdminWater() {
  const { t } = useLanguage()
  const [locations, setLocations] = useState([])
  const [selectedLoc, setSelectedLoc] = useState('all')
  const [series, setSeries] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Triage modal
  const [triageAlert, setTriageAlert] = useState(null)
  const [triageStatus, setTriageStatus] = useState('CONFIRMED')
  const [triageNotes, setTriageNotes] = useState('')
  const [savingTriage, setSavingTriage] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')

  async function loadData() {
    setError(null)
    try {
      const [locsRes, seriesRes, alertsRes] = await Promise.all([
        getWaterLocations(),
        getWaterSeries({ location_id: selectedLoc === 'all' ? undefined : selectedLoc }),
        getWaterAlerts(),
      ])

      setLocations(locsRes || [])
      setAlerts(alertsRes.alerts || [])

      const formattedSeries = (seriesRes.series || seriesRes.points || []).map((p) => {
        const timePart = p.timestamp ? p.timestamp.slice(11, 16) : ''
        const datePart = p.timestamp ? p.timestamp.slice(5, 10) : ''
        return {
          ...p,
          label: `${datePart} ${timePart}`,
        }
      })
      setSeries(formattedSeries)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [selectedLoc])

  function openTriage(alert) {
    setTriageAlert(alert)
    setTriageStatus(alert.status || 'CONFIRMED')
    setTriageNotes(alert.inspection_notes || '')
    setSuccessMsg('')
  }

  async function handleSaveTriage(e) {
    e.preventDefault()
    if (!triageAlert) return
    setSavingTriage(true)
    try {
      await patchWaterAlert(triageAlert.id, {
        status: triageStatus,
        inspection_notes: triageNotes,
      })
      setSuccessMsg(`Alert #${triageAlert.id} updated to ${triageStatus} successfully!`)
      setTriageAlert(null)
      await loadData()
    } catch (err) {
      alert(err.message || 'Failed to update alert')
    } finally {
      setSavingTriage(false)
    }
  }

  const suspectedCount = alerts.filter((a) => a.status === 'SUSPECTED').length
  const confirmedCount = alerts.filter((a) => a.status === 'CONFIRMED').length

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('adminNav.water')} Management & Night-Flow Intelligence</h1>
          <p>Continuous acoustic and pulse flow monitoring, nocturnal leak triage, and tank volume telemetry.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <label className="select-pill">
            <span className="visually-hidden">Location</span>
            <select value={selectedLoc} onChange={(e) => setSelectedLoc(e.target.value)}>
              <option value="all">All Monitoring Points</option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.building})
                </option>
              ))}
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

      {loading && !series.length && (
        <div aria-busy="true">
          <Skeleton height={100} radius={14} />
          <Skeleton height={360} radius={14} style={{ marginTop: 20 }} />
        </div>
      )}

      {!loading && (
        <>
          <section className="kpi-strip">
            <div className="kpi">
              <p className="kpi-label">Suspected Night Leaks</p>
              <div className="kpi-value" style={{ color: suspectedCount > 0 ? '#ea580c' : '#1f8a5b' }}>
                <strong>{suspectedCount} alerts</strong>
              </div>
              <p className="kpi-note">Flow exceeding 50 L/h between 02:00–05:00</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Confirmed Pipeline Fractures</p>
              <div className="kpi-value" style={{ color: confirmedCount > 0 ? '#dc2626' : '#1f8a5b' }}>
                <strong>{confirmedCount} confirmed</strong>
              </div>
              <p className="kpi-note">Triaged by maintenance technicians</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Monitored Ingestion Points</p>
              <div className="kpi-value">
                <strong>{locations.length} points</strong>
              </div>
              <p className="kpi-note">Overhead tanks, risers, washrooms</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Bucket Equivalence Baseline</p>
              <div className="kpi-value">
                <strong>15.0 L / bucket</strong>
              </div>
              <p className="kpi-note">Campus standard conservation conversion</p>
            </div>
          </section>

          {/* Water Flow Stream */}
          <section className="card card--chart" style={{ marginTop: 24 }}>
            <div className="card-head">
              <div>
                <h2>Hourly Flow Telemetry vs Inactive Baseline</h2>
                <p className="card-sub">Flow rate in litres per hour (L/h). Nocturnal peaks indicate hidden cistern leaks or valve overflow.</p>
              </div>
              <Droplet size={20} color="#0f8fa0" />
            </div>

            <div className="chart-box" style={{ height: 320, width: '100%', minHeight: 320 }}>
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={series} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0f8fa0" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#0f8fa0" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="waterBaseGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#6b7280' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} label={{ value: 'L/h', angle: -90, position: 'insideLeft' }} />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="flow_rate_lph" name="Actual Flow (L/h)" stroke="#0f8fa0" strokeWidth={2} fillOpacity={1} fill="url(#flowGrad)" />
                  <Area type="monotone" dataKey="baseline_lph" name="Nocturnal Baseline (L/h)" stroke="#64748b" strokeDasharray="4 4" fillOpacity={1} fill="url(#waterBaseGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Night Leak Alerts Table */}
          <section className="card" style={{ marginTop: 24 }}>
            <div className="card-head">
              <div>
                <h2>Nocturnal Leak Detection & Inspection Queue</h2>
                <p className="card-sub">Automated anomalies flagged during minimum active campus hours (02:00–05:00 AM).</p>
              </div>
              <ShieldAlert size={20} color="#ea580c" />
            </div>

            {alerts.length === 0 ? (
              <p className="empty-text" style={{ padding: 24 }}>No water leakage alerts currently open. All locations are operating within normal baseline.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#6b7280', fontSize: 13 }}>
                      <th style={{ padding: '10px 12px' }}>ID</th>
                      <th style={{ padding: '10px 12px' }}>Location</th>
                      <th style={{ padding: '10px 12px' }}>Avg Flow vs Baseline</th>
                      <th style={{ padding: '10px 12px' }}>Est. Waste</th>
                      <th style={{ padding: '10px 12px' }}>Status</th>
                      <th style={{ padding: '10px 12px' }}>Inspection Notes</th>
                      <th style={{ padding: '10px 12px' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.map((a) => (
                      <tr key={a.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '12px' }}><strong>#{a.id}</strong></td>
                        <td style={{ padding: '12px' }}>
                          <strong>{a.location_name}</strong>
                          <div style={{ fontSize: 12, color: '#6b7280' }}>{a.building}</div>
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span style={{ color: '#dc2626', fontWeight: 600 }}>{formatNumber(a.avg_flow_lph, 1)} L/h</span>
                          <span style={{ color: '#6b7280', fontSize: 12 }}> / {a.baseline_lph} L/h base</span>
                        </td>
                        <td style={{ padding: '12px' }}>
                          <strong>{formatNumber(a.excess_litres, 0)} L</strong>
                          <div style={{ fontSize: 11, color: '#6b7280' }}>~{Math.round(a.bucket_equivalents)} buckets</div>
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span
                            className="chip"
                            style={{
                              fontSize: 12,
                              padding: '2px 8px',
                              background: a.status === 'CONFIRMED' ? '#fef2f2' : a.status === 'SUSPECTED' ? '#fffbeb' : '#f0fdf4',
                              color: a.status === 'CONFIRMED' ? '#dc2626' : a.status === 'SUSPECTED' ? '#d97706' : '#16a34a',
                              borderColor: a.status === 'CONFIRMED' ? '#fecaca' : a.status === 'SUSPECTED' ? '#fde68a' : '#bbf7d0',
                            }}
                          >
                            {a.status}
                          </span>
                        </td>
                        <td style={{ padding: '12px', fontSize: 13, color: '#4b5563', maxWidth: 220 }}>
                          {a.inspection_notes || <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>Pending inspection</span>}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <button
                            type="button"
                            className="btn btn--outline"
                            style={{ padding: '6px 12px', fontSize: 13 }}
                            onClick={() => openTriage(a)}
                          >
                            Triage
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      {/* Triage Modal */}
      {triageAlert && (
        <div className="scrim" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="card" style={{ maxWidth: 520, width: '90%' }}>
            <div className="card-head">
              <h2>Triage Water Leak Alert #{triageAlert.id}</h2>
              <button type="button" className="icon-btn" onClick={() => setTriageAlert(null)}>✕</button>
            </div>

            <form onSubmit={handleSaveTriage} style={{ marginTop: 16 }}>
              <div style={{ padding: '10px 14px', background: '#f8fafc', borderRadius: 8, marginBottom: 16 }}>
                <strong>{triageAlert.location_name}</strong> ({triageAlert.building})
                <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                  Detected night flow: <strong>{triageAlert.avg_flow_lph} L/h</strong> vs baseline {triageAlert.baseline_lph} L/h
                </div>
              </div>

              <div className="field">
                <label htmlFor="triage-status">Inspection Classification</label>
                <div className="select-field">
                  <select
                    id="triage-status"
                    value={triageStatus}
                    onChange={(e) => setTriageStatus(e.target.value)}
                  >
                    <option value="SUSPECTED">SUSPECTED (Requires investigation)</option>
                    <option value="CONFIRMED">CONFIRMED (Physical leak verified)</option>
                    <option value="FALSE_ALARM">FALSE ALARM (Legitimate night utility usage)</option>
                  </select>
                </div>
              </div>

              <div className="field" style={{ marginTop: 14 }}>
                <label htmlFor="triage-notes">Technician Inspection Findings & Notes</label>
                <textarea
                  id="triage-notes"
                  rows={3}
                  value={triageNotes}
                  onChange={(e) => setTriageNotes(e.target.value)}
                  placeholder="e.g. Inspect washroom 2nd floor, replace faulty flush valve gasket"
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
                <button type="button" className="btn btn--outline" onClick={() => setTriageAlert(null)}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={savingTriage}>
                  {savingTriage ? <Loader2 size={16} className="spin" /> : 'Save Inspection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
