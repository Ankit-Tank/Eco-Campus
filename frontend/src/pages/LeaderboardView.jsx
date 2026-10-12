import { useEffect, useState } from 'react'
import {
  Award,
  ChevronDown,
  Info,
  Medal,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { getBlockLeaderboard } from '../services/leaderboardApi.js'
import { formatNumber } from '../utils/format.js'
import ErrorState from '../components/ui/ErrorState.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'

const GRADE_COLORS = {
  'A+': { bg: '#ecfdf5', text: '#047857', border: '#a7f3d0' },
  A: { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0' },
  B: { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
  C: { bg: '#fffbeb', text: '#d97706', border: '#fde68a' },
  D: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
}

const MEDAL_ICONS = ['🥇', '🥈', '🥉']

export default function LeaderboardView() {
  const { t } = useLanguage()
  const [period, setPeriod] = useState('7d')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function loadData() {
    setError(null)
    setLoading(true)
    try {
      const res = await getBlockLeaderboard(period)
      setData(res)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [period])

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Campus Block Sustainability Leaderboard</h1>
          <p>Gamified building efficiency rankings, letter grades, and avoidable ghost load scoring.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <label className="select-pill">
            <span className="visually-hidden">Period</span>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option value="today">Today</option>
              <option value="7d">Past 7 Days</option>
              <option value="14d">Past 14 Days</option>
              <option value="all">Full History</option>
            </select>
            <ChevronDown size={16} aria-hidden="true" />
          </label>

          <button type="button" className="btn btn--outline" onClick={loadData}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </header>

      {error && <ErrorState error={error} onRetry={loadData} />}

      {loading && (
        <div aria-busy="true">
          <div className="kpi-strip">
            {[0, 1, 2].map((i) => (
              <div className="kpi" key={i}>
                <Skeleton width={90} />
                <Skeleton height={36} width={130} style={{ marginTop: 10 }} />
              </div>
            ))}
          </div>
          <Skeleton height={340} radius={14} style={{ marginTop: 20 }} />
        </div>
      )}

      {data && !loading && (
        <>
          <section className="kpi-strip">
            <div className="kpi">
              <p className="kpi-label">Campus Efficiency Leader</p>
              <div className="kpi-value" style={{ color: '#047857' }}>
                <strong>
                  {(() => {
                    const top = (data.leaderboard || data.blocks || [])[0]
                    if (!top) return 'Block A'
                    const blk = top.block || 'A'
                    return blk.startsWith('Block') ? blk : `Block ${blk}`
                  })()}
                </strong>
              </div>
              <p className="kpi-note">Highest sustainability score ({(data.leaderboard || data.blocks || [])[0]?.score ?? (data.leaderboard || data.blocks || [])[0]?.sustainability_score ?? 0}/100)</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Total Avoidable Ghost Waste</p>
              <div className="kpi-value" style={{ color: '#dc2626' }}>
                <strong>{formatNumber(data.total_ghost_kwh || 0, 1)} kWh</strong>
              </div>
              <p className="kpi-note">Across all 3 campus academic blocks</p>
            </div>

            <div className="kpi">
              <p className="kpi-label">Cumulative Avoidable Cost</p>
              <div className="kpi-value" style={{ color: '#dc2626' }}>
                <strong>₹{formatNumber(data.total_cost_inr || 0, 2)}</strong>
              </div>
              <p className="kpi-note">Rate: ₹8.50/kWh commercial tariff</p>
            </div>
          </section>

          {/* Leaderboard Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20, marginTop: 24 }}>
            {(data.leaderboard || data.blocks || []).map((b, idx) => {
              const gradeStyle = GRADE_COLORS[b.grade] || GRADE_COLORS.B
              const blockTitle = b.block?.startsWith('Block') ? b.block : `Block ${b.block}`
              const scoreVal = b.score ?? b.sustainability_score ?? 0
              return (
                <section
                  key={b.block}
                  className="card"
                  style={{
                    position: 'relative',
                    borderTop: `4px solid ${idx === 0 ? '#10b981' : idx === 1 ? '#3b82f6' : '#f59e0b'}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <span style={{ fontSize: 24 }}>{MEDAL_ICONS[idx] || `#${b.rank}`}</span>
                      <h2 style={{ fontSize: 20, marginTop: 4 }}>{blockTitle}</h2>
                      <p style={{ fontSize: 13, color: '#64748b' }}>{b.name}</p>
                    </div>

                    <div
                      style={{
                        padding: '6px 14px',
                        borderRadius: 10,
                        background: gradeStyle.bg,
                        color: gradeStyle.text,
                        border: `1px solid ${gradeStyle.border}`,
                        fontSize: 22,
                        fontWeight: 800,
                        textAlign: 'center',
                      }}
                    >
                      {b.grade}
                      <div style={{ fontSize: 10, fontWeight: 500 }}>GRADE</div>
                    </div>
                  </div>

                  <div style={{ marginTop: 20, padding: '12px 16px', background: '#f8fafc', borderRadius: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: 13, color: '#64748b' }}>Sustainability Score</span>
                      <strong style={{ fontSize: 15, color: '#0f172a' }}>{scoreVal} / 100</strong>
                    </div>

                    {/* Progress Bar */}
                    <div style={{ width: '100%', height: 8, background: '#e2e8f0', borderRadius: 4, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${Math.min(100, Math.max(0, scoreVal))}%`,
                          height: '100%',
                          background: scoreVal > 80 ? '#10b981' : scoreVal > 65 ? '#3b82f6' : '#ef4444',
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                    <div style={{ padding: '8px 12px', background: '#f8fafc', borderRadius: 8 }}>
                      <div style={{ fontSize: 11, color: '#64748b' }}>Actual Draw</div>
                      <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>{formatNumber(b.actual_kwh, 1)} kWh</div>
                    </div>

                    <div style={{ padding: '8px 12px', background: '#fef2f2', borderRadius: 8 }}>
                      <div style={{ fontSize: 11, color: '#991b1b' }}>Ghost Load</div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#dc2626', marginTop: 2 }}>
                        {formatNumber(b.ghost_kwh, 1)} kWh ({b.waste_pct ?? b.waste_percentage ?? 0}%)
                      </div>
                    </div>

                    <div style={{ padding: '8px 12px', background: '#f8fafc', borderRadius: 8 }}>
                      <div style={{ fontSize: 11, color: '#64748b' }}>Avoidable Loss</div>
                      <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>₹{formatNumber(b.cost_inr, 2)}</div>
                    </div>

                    <div style={{ padding: '8px 12px', background: '#f8fafc', borderRadius: 8 }}>
                      <div style={{ fontSize: 11, color: '#64748b' }}>Carbon Footprint</div>
                      <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>{formatNumber(b.emissions_kg ?? b.co2_kg, 1)} kg</div>
                    </div>
                  </div>

                  <div style={{ marginTop: 14, fontSize: 12, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Zap size={14} color="#f59e0b" />
                    <span>Wastes equivalent of <strong>{Math.round(b.fan_equivalents || 0)} fan-hours</strong></span>
                  </div>
                </section>
              )
            })}
          </div>

          {/* Scoring Methodology Note */}
          <section className="card card--spaced" style={{ marginTop: 24 }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <Info size={22} color="#2563eb" />
              <div>
                <h3 style={{ fontSize: 16 }}>Leaderboard Scoring Methodology</h3>
                <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                  Sustainability Score is derived from the proportion of productive vs ghost energy:
                  <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4, marginLeft: 4 }}>
                    Score = 100 - (Ghost kWh / Actual kWh × 100)
                  </code>.
                  Grades are assigned as: <strong>A+ (90+)</strong>, <strong>A (80–89)</strong>, <strong>B (70–79)</strong>, <strong>C (60–69)</strong>, and <strong>D (&lt;60)</strong>.
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </>
  )
}
