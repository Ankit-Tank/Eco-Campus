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
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Info,
  Loader2,
  PowerOff,
  RefreshCw,
  Zap,
} from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getElectricitySeries } from '../../services/electricityApi.js'
import {
  explainRoomGhost,
  getGhostCurrent,
  getGhostRanking,
  getSwitchOffList,
} from '../../services/ghostLoadApi.js'
import { switchOffAppliance } from '../../services/savingsApi.js'
import { formatNumber } from '../../utils/format.js'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'

const REASON_COLORS = {
  NO_CLASS_AC_ON: '#dc2626',
  LAB_AFTER_HOURS: '#ea580c',
  OVER_EXPECTED_DURING_CLASS: '#d97706',
  OUTSIDE_SCHEDULE: '#7c3aed',
  IDLE_BASELINE: '#059669',
}

export default function AdminElectricity() {
  const { t } = useLanguage()
  const [block, setBlock] = useState('all')
  const [period, setPeriod] = useState('week')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [seriesData, setSeriesData] = useState([])
  const [currentGhost, setCurrentGhost] = useState(null)
  const [ranking, setRanking] = useState([])
  const [switchOffList, setSwitchOffList] = useState([])

  // Explain modal state
  const [explainRoomId, setExplainRoomId] = useState(null)
  const [explainData, setExplainData] = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)

  // Action status
  const [actionSuccess, setActionSuccess] = useState('')
  const [actionLoading, setActionLoading] = useState(null)

  async function loadData() {
    setError(null)
    try {
      const [seriesRes, currentRes, rankingRes, switchRes] = await Promise.all([
        getElectricitySeries({ block: block === 'all' ? undefined : block, limit: 500 }),
        getGhostCurrent(),
        getGhostRanking({ period }),
        getSwitchOffList(),
      ])

      // Aggregate per-room readings by timestamp for campus/block telemetry stream
      const pointsByTimestamp = new Map()
      const rawPoints = seriesRes.series || seriesRes.points || []

      for (const p of rawPoints) {
        const ts = p.timestamp || ''
        const actual = Number(p.actual_kw ?? p.actual_demand_kw ?? 0)
        const expected = Number(p.expected_kw ?? p.expected_demand_kw ?? 0)
        const ghost = Number(p.ghost_kw ?? p.ghost_load_kw ?? 0)

        if (!pointsByTimestamp.has(ts)) {
          const timePart = ts ? ts.slice(11, 16) : ''
          const datePart = ts ? ts.slice(5, 10) : ''
          pointsByTimestamp.set(ts, {
            timestamp: ts,
            label: `${datePart} ${timePart}`,
            actual_kw: actual,
            expected_kw: expected,
            ghost_kw: ghost,
          })
        } else {
          const existing = pointsByTimestamp.get(ts)
          existing.actual_kw = Math.round((existing.actual_kw + actual) * 1000) / 1000
          existing.expected_kw = Math.round((existing.expected_kw + expected) * 1000) / 1000
          existing.ghost_kw = Math.round((existing.ghost_kw + ghost) * 1000) / 1000
        }
      }

      const chartPoints = Array.from(pointsByTimestamp.values())
        .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
        .slice(-32)

      setSeriesData(chartPoints)
      setCurrentGhost({
        ...currentRes,
        total_actual_kw: currentRes?.total_actual_kw ?? currentRes?.actual_kw ?? 0,
        total_expected_kw: currentRes?.total_expected_kw ?? currentRes?.expected_kw ?? 0,
        total_ghost_kw: currentRes?.total_ghost_kw ?? currentRes?.ghost_kw ?? 0,
        cost_per_hour_inr: currentRes?.cost_per_hour_inr ?? currentRes?.cost_per_hour ?? ((currentRes?.total_ghost_kw || 0) * 8.5),
        fan_equivalents: currentRes?.fan_equivalents ?? currentRes?.fan_equivalent ?? 0,
      })
      setRanking(
        (rankingRes.ranking || []).map((r) => ({
          ...r,
          ghost_kwh: r.ghost_kwh ?? r.total_ghost_kwh ?? 0,
          room_name: r.room_name ?? r.name ?? '',
        }))
      )
      setSwitchOffList(switchRes.items || [])
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const timer = setInterval(loadData, 12000)
    return () => clearInterval(timer)
  }, [block, period])

  async function handleSwitchOff(item) {
    setActionLoading(item.equipment_id)
    setActionSuccess('')
    try {
      await switchOffAppliance({
        room_id: item.room_id,
        equipment_id: item.equipment_id,
        notes: `Turned off ${item.equipment_kind} from Electricity priority panel`,
      })
      setActionSuccess(`Successfully sent switch-off command for ${item.equipment_kind} in ${item.room_code}! Closed-loop verification initiated.`)
      await loadData()
    } catch (err) {
      alert(err.message || 'Failed to switch off appliance')
    } finally {
      setActionLoading(null)
    }
  }

  async function openExplain(roomId) {
    setExplainRoomId(roomId)
    setExplainLoading(true)
    try {
      const data = await explainRoomGhost(roomId)
      setExplainData(data)
    } catch (err) {
      alert('Could not fetch room explainability details.')
    } finally {
      setExplainLoading(false)
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('adminNav.electricity')} & Ghost Load Intelligence</h1>
          <p>Real-time visual telemetry, AI demand baselines, and prioritized appliance switch-off.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <label className="select-pill">
            <span className="visually-hidden">Block</span>
            <select value={block} onChange={(e) => setBlock(e.target.value)}>
              <option value="all">All Blocks</option>
              <option value="A">Block A</option>
              <option value="B">Block B</option>
              <option value="C">Block C</option>
            </select>
          </label>

          <label className="select-pill">
            <span className="visually-hidden">Period</span>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option value="day">Today</option>
              <option value="week">Past 7 Days</option>
              <option value="month">Past 30 Days</option>
            </select>
          </label>

          <button type="button" className="btn btn--outline" onClick={loadData} title="Refresh Telemetry">
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </header>

      {actionSuccess && (
        <div className="state-box" style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#065f46', marginBottom: 20 }}>
          <CheckCircle size={22} color="#059669" />
          <div>
            <strong>Action Executed</strong>
            <p>{actionSuccess}</p>
          </div>
        </div>
      )}

      {error && <ErrorState error={error} onRetry={loadData} />}

      {loading && !currentGhost && (
        <div aria-busy="true">
          <div className="kpi-strip">
            {[0, 1, 2, 3].map((i) => (
              <div className="kpi" key={i}>
                <Skeleton width={90} />
                <Skeleton height={36} width={130} style={{ marginTop: 10 }} />
              </div>
            ))}
          </div>
          <Skeleton height={380} radius={14} style={{ marginTop: 20 }} />
        </div>
      )}

      {currentGhost && (
        <>
          <section className="kpi-strip">
            <div className="kpi">
              <p className="kpi-label">Instantaneous Actual Load</p>
              <div className="kpi-value">
                <strong>{formatNumber(currentGhost.total_actual_kw, 1)} kW</strong>
              </div>
              <p className="kpi-note">Live campus smart meter sum</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Timetable Expected Demand</p>
              <div className="kpi-value">
                <strong>{formatNumber(currentGhost.total_expected_kw, 1)} kW</strong>
              </div>
              <p className="kpi-note">Scheduled classroom requirement</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Current Ghost Load (Waste)</p>
              <div className="kpi-value" style={{ color: currentGhost.total_ghost_kw > 1 ? '#dc2626' : '#1f8a5b' }}>
                <strong>{formatNumber(currentGhost.total_ghost_kw, 1)} kW</strong>
              </div>
              <p className="kpi-note">₹{formatNumber(currentGhost.cost_per_hour_inr, 2)} / hr running loss</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Equivalent Ceiling Fans</p>
              <div className="kpi-value">
                <strong>{formatNumber(currentGhost.fan_equivalents, 0)} fans</strong>
              </div>
              <p className="kpi-note">Assuming 75W standard fan</p>
            </div>
          </section>

          {/* Telemetry Chart */}
          <section className="card card--chart" style={{ marginTop: 24 }}>
            <div className="card-head">
              <div>
                <h2>Electricity Telemetry & Ghost Load Stream</h2>
                <p className="card-sub">Comparing actual draw vs academic expected baseline at 15-minute intervals.</p>
              </div>
            </div>

            <div className="chart-box" style={{ height: 320, width: '100%', minHeight: 320 }}>
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={seriesData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1e3a8a" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#1e3a8a" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="expectedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#059669" stopOpacity={0.7} />
                      <stop offset="95%" stopColor="#059669" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="ghostGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#dc2626" stopOpacity={0.7} />
                      <stop offset="95%" stopColor="#dc2626" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#6b7280' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} label={{ value: 'kW', angle: -90, position: 'insideLeft' }} />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="actual_kw" name="Actual Load" stroke="#1e3a8a" fillOpacity={1} fill="url(#actualGrad)" />
                  <Area type="monotone" dataKey="expected_kw" name="Expected Baseline" stroke="#059669" fillOpacity={1} fill="url(#expectedGrad)" />
                  <Area type="monotone" dataKey="ghost_kw" name="Ghost Load (Excess)" stroke="#dc2626" fillOpacity={1} fill="url(#ghostGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Switch-Off Priority Panel & Ghost Ranking */}
          <div className="grid-2" style={{ marginTop: 24, gap: 20 }}>
            {/* Switch Off Priority List */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Switch-Off-First Actions</h2>
                  <p className="card-sub">Ranked actionable appliances currently operating in unattended spaces.</p>
                </div>
                <Zap size={20} color="#ea580c" />
              </div>

              {switchOffList.length === 0 ? (
                <p className="empty-text" style={{ padding: 24 }}>No high-waste appliances detected in empty rooms right now.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table className="table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#6b7280', fontSize: 13 }}>
                        <th style={{ padding: '8px 12px' }}>Room</th>
                        <th style={{ padding: '8px 12px' }}>Appliance</th>
                        <th style={{ padding: '8px 12px' }}>Waste</th>
                        <th style={{ padding: '8px 12px' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {switchOffList.slice(0, 6).map((item) => (
                        <tr key={`${item.room_id}-${item.equipment_id}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                          <td style={{ padding: '12px' }}>
                            <strong>{item.room_code}</strong>
                            <div style={{ fontSize: 12, color: '#6b7280' }}>Block {item.block}</div>
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span style={{ textTransform: 'capitalize' }}>{item.equipment_kind}</span>
                            <div style={{ fontSize: 12, color: '#dc2626' }}>{item.reason_code}</div>
                          </td>
                          <td style={{ padding: '12px', fontWeight: 600, color: '#dc2626' }}>
                            +{formatNumber(item.ghost_kw, 2)} kW
                          </td>
                          <td style={{ padding: '12px' }}>
                            <button
                              type="button"
                              className="btn btn--primary"
                              style={{ padding: '6px 12px', fontSize: 13, background: '#dc2626' }}
                              disabled={actionLoading === item.equipment_id}
                              onClick={() => handleSwitchOff(item)}
                            >
                              {actionLoading === item.equipment_id ? (
                                <Loader2 size={14} className="spin" />
                              ) : (
                                <>
                                  <PowerOff size={14} /> Turn Off
                                </>
                              )}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Room Ghost Ranking */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Ghost Load Ranking</h2>
                  <p className="card-sub">Top rooms by cumulative ghost waste over the selected period.</p>
                </div>
                <AlertTriangle size={20} color="#dc2626" />
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table className="table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#6b7280', fontSize: 13 }}>
                      <th style={{ padding: '8px 12px' }}>#</th>
                      <th style={{ padding: '8px 12px' }}>Room</th>
                      <th style={{ padding: '8px 12px' }}>Ghost kWh</th>
                      <th style={{ padding: '8px 12px' }}>Primary Cause</th>
                      <th style={{ padding: '8px 12px' }}>Explain</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ranking.slice(0, 8).map((r, idx) => (
                      <tr key={r.room_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '10px 12px', color: '#6b7280', fontWeight: 600 }}>{idx + 1}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <strong>{r.room_code}</strong>
                          <div style={{ fontSize: 11, color: '#6b7280' }}>{r.room_name}</div>
                        </td>
                        <td style={{ padding: '10px 12px', fontWeight: 700, color: '#dc2626' }}>
                          {formatNumber(r.ghost_kwh, 1)} kWh
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <span
                            className="chip"
                            style={{
                              fontSize: 11,
                              padding: '2px 8px',
                              background: '#fef2f2',
                              color: REASON_COLORS[r.dominant_reason_code] || '#dc2626',
                              borderColor: '#fecaca',
                            }}
                          >
                            {r.dominant_reason_code || 'IDLE_WASTE'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <button
                            type="button"
                            className="btn btn--outline"
                            style={{ padding: '4px 8px', fontSize: 12 }}
                            onClick={() => openExplain(r.room_id)}
                          >
                            <Info size={13} /> View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </>
      )}

      {/* Room Explainability Modal */}
      {explainRoomId && (
        <div className="scrim" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="card" style={{ maxWidth: 540, width: '90%', maxHeight: '85vh', overflowY: 'auto' }}>
            <div className="card-head">
              <h2>Diagnostic Explainability Breakdown</h2>
              <button type="button" className="icon-btn" onClick={() => setExplainRoomId(null)}>✕</button>
            </div>

            {explainLoading && <Skeleton height={200} />}

            {explainData && (
              <div style={{ marginTop: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #eee', paddingBottom: 10 }}>
                  <div>
                    <h3 style={{ fontSize: 18 }}>{explainData.room_code} - {explainData.room_name}</h3>
                    <p style={{ fontSize: 13, color: '#666' }}>Block {explainData.block} · Status: <strong>{explainData.status}</strong></p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 20, fontWeight: 700, color: '#dc2626' }}>+{formatNumber(explainData.ghost_kw, 2)} kW</div>
                    <span style={{ fontSize: 12, color: '#888' }}>Ghost Load</span>
                  </div>
                </div>

                <div style={{ marginTop: 16 }}>
                  <h4>Root Cause Classification</h4>
                  <p style={{ background: '#fef2f2', borderLeft: '4px solid #dc2626', padding: '10px 14px', borderRadius: 6, fontSize: 14 }}>
                    <strong>{explainData.primary_reason_code}:</strong> {explainData.explanation}
                  </p>
                </div>

                <div style={{ marginTop: 16 }}>
                  <h4>Recommended Operator Action</h4>
                  <p style={{ background: '#ecfdf5', borderLeft: '4px solid #059669', padding: '10px 14px', borderRadius: 6, fontSize: 14 }}>
                    {explainData.recommended_action}
                  </p>
                </div>

                <div style={{ marginTop: 20, textAlign: 'right' }}>
                  <button type="button" className="btn btn--primary" onClick={() => setExplainRoomId(null)}>Close</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
