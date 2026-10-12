import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  FastForward,
  Gauge,
  Loader2,
  Pause,
  Play,
  Power,
  RefreshCw,
  RotateCcw,
  Sparkles,
  Zap,
} from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import {
  getLiveSnapshot,
  getSimState,
  pauseSim,
  resetSim,
  setApplianceState,
  setSimSpeed,
  startSim,
  tickSim,
  triggerDemoScenario,
} from '../../services/simulatorApi.js'
import { getRooms, getRoomEquipment } from '../../services/roomsApi.js'
import { switchOffAppliance } from '../../services/savingsApi.js'
import { formatNumber } from '../../utils/format.js'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'

export default function AdminSimulator() {
  const { t } = useLanguage()
  const [simState, setSimState] = useState(null)
  const [snapshot, setSnapshot] = useState(null)
  const [rooms, setRooms] = useState([])
  const [selectedRoomId, setSelectedRoomId] = useState('')
  const [equipmentList, setEquipmentList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Demo status
  const [demoTriggered, setDemoTriggered] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [actionSuccess, setActionSuccess] = useState('')
  const [speedLoading, setSpeedLoading] = useState(false)

  async function loadData() {
    try {
      const [stateRes, snapRes] = await Promise.all([
        getSimState(),
        getLiveSnapshot(),
      ])
      setSimState(stateRes)
      setSnapshot(snapRes)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    getRooms().then((res) => {
      const list = Array.isArray(res) ? res : (res?.items || res?.rooms || [])
      setRooms(list)
    })
    const timer = setInterval(loadData, 2000) // Fast polling for real-time simulation clock
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (selectedRoomId) {
      getRoomEquipment(selectedRoomId).then((res) => {
        const list = Array.isArray(res) ? res : (res?.items || res?.equipment || [])
        setEquipmentList(list)
      })
    }
  }, [selectedRoomId])

  async function handleTogglePlay() {
    if (!simState) return
    try {
      if (simState.running) {
        await pauseSim()
      } else {
        await startSim()
      }
      await loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  async function handleSetSpeed(newSpeed) {
    setSpeedLoading(true)
    try {
      await setSimSpeed(newSpeed)
      await loadData()
    } catch (err) {
      alert(err.message)
    } finally {
      setSpeedLoading(false)
    }
  }

  async function handleTick() {
    try {
      await tickSim(15)
      await loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  async function handleDemoScenario() {
    setDemoLoading(true)
    setActionSuccess('')
    try {
      const res = await triggerDemoScenario()
      setDemoTriggered(true)
      setActionSuccess('Demo scenario activated! Virtual clock reset to 21:30 (evening), speed set to 60x, AC turned ON in A-102. Alarm is now active!')
      await loadData()
    } catch (err) {
      alert(err.message || 'Failed to trigger demo')
    } finally {
      setDemoLoading(false)
    }
  }

  async function handleApplianceToggle(eq) {
    const newState = eq.state === 'ON' ? 'OFF' : 'ON'
    try {
      await setApplianceState({ equipment_id: eq.id, state: newState })
      const updated = await getRoomEquipment(selectedRoomId)
      setEquipmentList(updated || [])
      await loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Telemetry Simulator & Hackathon Demo Console</h1>
          <p>Accelerate time, inject deliberate waste events, and verify closed-loop savings in seconds.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <button
            type="button"
            className="btn btn--primary"
            style={{ background: '#7c3aed', borderColor: '#7c3aed' }}
            onClick={handleDemoScenario}
            disabled={demoLoading}
          >
            {demoLoading ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />}
            Trigger 30-Sec Demo Scenario
          </button>
        </div>
      </header>

      {actionSuccess && (
        <div className="state-box" style={{ background: '#f5f3ff', borderColor: '#ddd6fe', color: '#5b21b6', marginBottom: 20 }}>
          <Sparkles size={22} color="#7c3aed" />
          <div>
            <strong>Demo Scenario Active</strong>
            <p>{actionSuccess}</p>
          </div>
        </div>
      )}

      {error && <ErrorState error={error} onRetry={loadData} />}

      {loading && !simState && (
        <div aria-busy="true">
          <Skeleton height={140} radius={14} />
          <Skeleton height={340} radius={14} style={{ marginTop: 20 }} />
        </div>
      )}

      {simState && (
        <>
          {/* Virtual Clock & Playback Bar */}
          <section className="card" style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)', color: '#fff', border: 'none' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Virtual Simulation Clock</div>
                <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'monospace', color: '#38bdf8', marginTop: 4 }}>
                  {simState.virtual_now ? simState.virtual_now.replace('T', ' ').slice(0, 19) : 'Initializing...'}
                </div>
                <div style={{ fontSize: 13, color: '#cbd5e1', marginTop: 4 }}>
                  Clock status: <strong style={{ color: simState.running ? '#4ade80' : '#f87171' }}>{simState.running ? 'RUNNING' : 'PAUSED'}</strong> · Speed: <strong>{simState.speed}x</strong>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn"
                  style={{ background: simState.running ? '#e11d48' : '#16a34a', color: '#fff', border: 'none', padding: '10px 18px' }}
                  onClick={handleTogglePlay}
                >
                  {simState.running ? <><Pause size={18} /> Pause</> : <><Play size={18} /> Start Clock</>}
                </button>

                <button
                  type="button"
                  className="btn btn--outline"
                  style={{ color: '#fff', borderColor: '#475569' }}
                  onClick={handleTick}
                >
                  <FastForward size={16} /> +15 Min
                </button>

                {/* Speed Multipliers */}
                <div style={{ display: 'flex', background: '#334155', borderRadius: 8, padding: 3 }}>
                  {[1, 10, 60, 120].map((s) => (
                    <button
                      key={s}
                      type="button"
                      style={{
                        padding: '6px 12px',
                        fontSize: 12,
                        borderRadius: 6,
                        border: 'none',
                        background: simState.speed === s ? '#38bdf8' : 'transparent',
                        color: simState.speed === s ? '#0f172a' : '#e2e8f0',
                        fontWeight: simState.speed === s ? 700 : 500,
                        cursor: 'pointer',
                      }}
                      onClick={() => handleSetSpeed(s)}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Live Snapshot KPIs */}
          {snapshot && (
            <section className="kpi-strip" style={{ marginTop: 24 }}>
              <div className="kpi">
                <p className="kpi-label">Live Campus Demand</p>
                <div className="kpi-value">
                  <strong>{formatNumber(snapshot.total_actual_kw, 2)} kW</strong>
                </div>
                <p className="kpi-note">Expected: {formatNumber(snapshot.total_expected_kw, 2)} kW</p>
              </div>

              <div className="kpi">
                <p className="kpi-label">Instantaneous Ghost Load</p>
                <div className="kpi-value" style={{ color: snapshot.total_ghost_kw > 1 ? '#dc2626' : '#1f8a5b' }}>
                  <strong>{formatNumber(snapshot.total_ghost_kw, 2)} kW</strong>
                </div>
                <p className="kpi-note">Running cost: ₹{formatNumber(snapshot.cost_per_hour_inr, 2)} / hr</p>
              </div>

              <div className="kpi">
                <p className="kpi-label">Hourly Carbon Emissions</p>
                <div className="kpi-value">
                  <strong>{formatNumber(snapshot.co2_per_hour_kg, 2)} kg/hr</strong>
                </div>
                <p className="kpi-note">0.71 kg CO₂ / kWh intensity</p>
              </div>

              <div className="kpi">
                <p className="kpi-label">Active Alarm Count</p>
                <div className="kpi-value" style={{ color: (snapshot.active_alerts || []).length > 0 ? '#ea580c' : '#1f8a5b' }}>
                  <strong>{(snapshot.active_alerts || []).length} alarms</strong>
                </div>
                <p className="kpi-note">Rooms exceeding threshold</p>
              </div>
            </section>
          )}

          {/* Room Statuses & Appliance Overrides */}
          <div className="grid-2" style={{ marginTop: 24, gap: 20 }}>
            {/* Live Room Statuses */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Instantaneous Room Statuses</h2>
                  <p className="card-sub">Classroom occupancy & academic state at virtual timestamp.</p>
                </div>
                <Clock size={20} color="#64748b" />
              </div>

              <div style={{ maxHeight: 380, overflowY: 'auto' }}>
                <table className="table" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#6b7280', fontSize: 12 }}>
                      <th style={{ padding: '8px' }}>Room</th>
                      <th style={{ padding: '8px' }}>Draw</th>
                      <th style={{ padding: '8px' }}>Ghost</th>
                      <th style={{ padding: '8px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(snapshot?.rooms || []).map((r) => (
                      <tr key={r.room_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '10px 8px' }}>
                          <strong>{r.room_code}</strong>
                          <div style={{ fontSize: 11, color: '#6b7280' }}>Block {r.block}</div>
                        </td>
                        <td style={{ padding: '10px 8px', fontSize: 13 }}>{formatNumber(r.actual_kw, 1)} kW</td>
                        <td style={{ padding: '10px 8px', fontSize: 13, color: r.ghost_kw > 0.5 ? '#dc2626' : '#1f8a5b', fontWeight: 600 }}>
                          +{formatNumber(r.ghost_kw, 2)} kW
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <span
                            className="chip"
                            style={{
                              fontSize: 11,
                              padding: '2px 6px',
                              background: r.status === 'High Usage' ? '#fef2f2' : '#f0fdf4',
                              color: r.status === 'High Usage' ? '#dc2626' : '#16a34a',
                              borderColor: r.status === 'High Usage' ? '#fecaca' : '#bbf7d0',
                            }}
                          >
                            {r.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Manual Appliance State Controller */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Interactive Appliance Controller</h2>
                  <p className="card-sub">Manually toggle loads to test sensor telemetry reactions.</p>
                </div>
                <Power size={20} color="#7c3aed" />
              </div>

              <div className="field">
                <label htmlFor="sim-room-select">Choose Room</label>
                <div className="select-field">
                  <select
                    id="sim-room-select"
                    value={selectedRoomId}
                    onChange={(e) => setSelectedRoomId(e.target.value)}
                  >
                    <option value="">Select a room...</option>
                    {rooms.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.room_code} - {r.room_name || r.name} (Block {r.block})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {selectedRoomId && (
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ fontSize: 13, color: '#64748b', textTransform: 'uppercase', marginBottom: 10 }}>Installed Equipment</h4>
                  {equipmentList.length === 0 ? (
                    <p className="empty-text">Loading room equipment...</p>
                  ) : (
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {equipmentList.map((eq) => (
                        <li
                          key={eq.id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px 14px',
                            background: '#f8fafc',
                            borderRadius: 8,
                            border: '1px solid #e2e8f0',
                          }}
                        >
                          <div>
                            <strong style={{ textTransform: 'capitalize' }}>{eq.kind} ({eq.count}x)</strong>
                            <div style={{ fontSize: 12, color: '#64748b' }}>
                              Rated: {eq.rated_kw} kW each | State: <strong style={{ color: eq.state === 'ON' ? '#16a34a' : '#64748b' }}>{eq.state}</strong>
                            </div>
                          </div>
                          <button
                            type="button"
                            className="btn"
                            style={{
                              padding: '6px 14px',
                              fontSize: 12,
                              background: eq.state === 'ON' ? '#dc2626' : '#16a34a',
                              color: '#fff',
                              border: 'none',
                            }}
                            onClick={() => handleApplianceToggle(eq)}
                          >
                            Toggle {eq.state === 'ON' ? 'OFF' : 'ON'}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </>
  )
}
