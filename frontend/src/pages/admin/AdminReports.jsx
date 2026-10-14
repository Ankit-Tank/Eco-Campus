import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Award,
  Calendar,
  CheckCircle,
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  RefreshCw,
  TrendingDown,
  Zap,
} from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { downloadReportCsv, getReportsSummary } from '../../services/reportsApi.js'
import { getSimState } from '../../services/simulatorApi.js'
import { formatNumber, lastDays } from '../../utils/format.js'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'

// Reports cover the last N days ending at the SIMULATION clock (not today's real date), because
// that is where the generated readings live.
async function simAnchoredRange(days) {
  try {
    const sim = await getSimState()
    if (sim?.virtual_now) return lastDays(days, new Date(sim.virtual_now))
  } catch {
    // fall back to today's date below
  }
  return lastDays(days)
}

export default function AdminReports() {
  const { t } = useLanguage()
  const [days, setDays] = useState(14)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')

  async function loadData() {
    setError(null)
    setLoading(true)
    try {
      const range = await simAnchoredRange(days)
      const res = await getReportsSummary({ from: range.from, to: range.to })
      setData(res)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [days])

  async function handleExportCsv() {
    setDownloading(true)
    setDownloadError('')
    try {
      const range = await simAnchoredRange(days)
      await downloadReportCsv({
        from: range.from,
        to: range.to,
        filename: `ghostwatt_sustainability_audit_${range.from}_${range.to}.csv`,
      })
    } catch (err) {
      setDownloadError('Failed to download CSV: ' + err.message)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('adminNav.reports')} & Sustainability Audit</h1>
          <p>Auditable campus sustainability reports, recommended interventions, and raw CSV exports.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <label className="select-pill">
            <Calendar size={16} aria-hidden="true" />
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Past 7 Days</option>
              <option value={14}>Past 14 Days</option>
              <option value={30}>Past 30 Days</option>
            </select>
          </label>

          <button
            type="button"
            className="btn btn--primary"
            onClick={handleExportCsv}
            disabled={downloading}
          >
            {downloading ? <Loader2 size={16} className="spin" /> : <Download size={16} />}
            Download CSV Export
          </button>
        </div>
      </header>

      {downloadError && (
        <p className="alert-note" role="alert">
          {downloadError}
        </p>
      )}

      {error && <ErrorState error={error} onRetry={loadData} />}

      {loading && (
        <div aria-busy="true">
          <div className="kpi-strip">
            {[0, 1, 2, 3].map((i) => (
              <div className="kpi" key={i}>
                <Skeleton width={90} />
                <Skeleton height={36} width={130} style={{ marginTop: 10 }} />
              </div>
            ))}
          </div>
          <Skeleton height={320} radius={14} style={{ marginTop: 20 }} />
        </div>
      )}

      {data && !loading && (
        <>
          <section className="kpi-strip">
            <div className="kpi">
              <p className="kpi-label">Cumulative Energy Waste</p>
              <div className="kpi-value" style={{ color: '#dc2626' }}>
                <strong>{formatNumber(data.summary?.total_ghost_kwh || 0, 1)} kWh</strong>
              </div>
              <p className="kpi-note">{data.summary?.ghost_pct_of_actual || 0}% of total consumption</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Avoidable Financial Loss</p>
              <div className="kpi-value" style={{ color: '#dc2626' }}>
                <strong>₹{formatNumber(data.summary?.total_rupees_lost || 0, 2)}</strong>
              </div>
              <p className="kpi-note">Rate: ₹8.50 per commercial kWh</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Carbon Impact</p>
              <div className="kpi-value">
                <strong>{formatNumber(data.summary?.total_co2_kg || 0, 1)} kg</strong>
              </div>
              <p className="kpi-note">0.71 kg CO₂ / kWh grid factor</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Verified Savings Realized</p>
              <div className="kpi-value" style={{ color: '#059669' }}>
                <strong>{formatNumber(data.verified_savings?.total_kwh_reduced || 0, 1)} kWh</strong>
              </div>
              <p className="kpi-note">₹{formatNumber(data.verified_savings?.total_rupees_saved || 0, 2)} saved post-intervention</p>
            </div>
          </section>

          {/* Top Wasting Rooms & Recommendations */}
          <div className="grid-2" style={{ marginTop: 24, gap: 20 }}>
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Top 3 Ghost Load Inefficiencies</h2>
                  <p className="card-sub">Rooms with highest avoidable consumption during the audit window.</p>
                </div>
                <AlertTriangle size={20} color="#dc2626" />
              </div>

              {(!data.top_rooms || data.top_rooms.length === 0) ? (
                <p className="empty-text">No significant inefficiencies detected.</p>
              ) : (
                <ul className="report-list">
                  {data.top_rooms.map((room, idx) => (
                    <li key={room.room_id} className="report-row" style={{ alignItems: 'flex-start' }}>
                      <span
                        style={{
                          width: 26,
                          height: 26,
                          borderRadius: '50%',
                          background: '#fef2f2',
                          color: '#dc2626',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: 12,
                        }}
                      >
                        {idx + 1}
                      </span>
                      <div className="report-text" style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <strong>{room.room_code} · {room.room_name}</strong>
                          <span style={{ color: '#dc2626', fontWeight: 700 }}>{formatNumber(room.ghost_kwh, 1)} kWh</span>
                        </div>
                        <div style={{ fontSize: 13, color: '#4b5563', marginTop: 4 }}>
                          {room.explanation}
                        </div>
                        <div style={{ fontSize: 12, color: '#059669', marginTop: 4, fontWeight: 500 }}>
                          Action: {room.recommended_action}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Recommended Interventions */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Recommended Interventions</h2>
                  <p className="card-sub">AI policy and maintenance directives for facility administration.</p>
                </div>
                <Award size={20} color="#059669" />
              </div>

              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                {(data.recommended_actions || [
                  'Automate evening patrol sweep for Block A Classrooms at 21:00.',
                  'Enforce central relay shut-off for computer labs 30 minutes after last timetable slot.',
                  'Repair nocturnal washroom valve leaks in Block C risers.',
                ]).map((action, i) => (
                  <li
                    key={i}
                    style={{
                      padding: '12px 14px',
                      background: '#f8fafc',
                      borderRadius: 8,
                      borderLeft: '4px solid #1f8a5b',
                      fontSize: 13,
                      color: '#1e293b',
                    }}
                  >
                    {action}
                  </li>
                ))}
              </ul>

              <div style={{ marginTop: 24, padding: '14px', background: '#ecfdf5', borderRadius: 8 }}>
                <strong style={{ color: '#065f46' }}>Verified Closed-Loop Crediting</strong>
                <p style={{ fontSize: 12, color: '#047857', marginTop: 4 }}>
                  All savings reported are strictly validated against pre-action and post-action 15-minute smart meter intervals. Drops caused by normal class conclusions are mathematically excluded.
                </p>
              </div>
            </section>
          </div>
        </>
      )}
    </>
  )
}
