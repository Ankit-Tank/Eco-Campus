import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getLiveSnapshot } from '../../services/simulatorApi.js'
import { getSavingsSummary } from '../../services/savingsApi.js'
import { getWaterAlerts } from '../../services/waterApi.js'
import { formatDate, formatNumber } from '../../utils/format.js'

function Kpi({ label, value, unit, note }) {
  return (
    <div className="kpi">
      <p className="kpi-label">{label}</p>
      <div className="kpi-value">
        <strong>
          {value} {unit}
        </strong>
      </div>
      {note && <p className="kpi-note">{note}</p>}
    </div>
  )
}

// Read-only view of what the campus is using right now. Students never see admin controls here;
// the backend only exposes read endpoints to this role.
export default function StudentCampus() {
  const { t, language } = useLanguage()
  // Refreshes every 4 seconds to keep the numbers "live".
  const live = useApi(() => getLiveSnapshot(), [], { interval: 4000 })
  const savings = useApi(() => getSavingsSummary(), [], { interval: 15000 })
  const water = useApi(() => getWaterAlerts(), [], { interval: 30000 })

  const snap = live.data
  const topRooms = snap ? [...snap.rooms].filter((r) => r.ghost_kw > 0).sort((a, b) => b.ghost_kw - a.ghost_kw).slice(0, 5) : []
  const alerts = (water.data?.alerts || []).slice(0, 3)
  const s = savings.data

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('campus.title')}</h1>
          <p>{t('campus.subtitle')}</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
          {snap?.virtual_now && (
            <span className="pill-muted" style={{ marginLeft: 8 }}>
              {t('campus.updated')}: {snap.virtual_now.replace('T', ' ').slice(0, 16)}
            </span>
          )}
        </div>
      </header>

      {live.status === 'error' && <ErrorState error={live.error} onRetry={live.reload} />}
      {live.status === 'loading' && !snap && <Skeleton height={140} radius={14} />}

      {snap && (
        <>
          <section className="kpi-strip kpi-strip--4" aria-label={t('campus.ghostNow')}>
            <Kpi label={t('campus.ghostNow')} value={formatNumber(snap.total_ghost_kw, 2)} unit={t('units2.kw')} note={`${t('campus.actual')}: ${formatNumber(snap.total_actual_kw, 2)} ${t('units2.kw')} · ${t('campus.expected')}: ${formatNumber(snap.total_expected_kw, 2)} ${t('units2.kw')}`} />
            <Kpi label={t('campus.costPerHour')} value={`₹${formatNumber(snap.cost_per_hour, 2)}`} unit="" note={snap.assumptions?.tariff} />
            <Kpi label={t('campus.co2PerHour')} value={formatNumber(snap.co2_per_hour, 2)} unit={t('units2.kg')} note={snap.assumptions?.emissions} />
            <Kpi label={t('campus.equivalent')} value={formatNumber(snap.fan_equivalent, 0)} unit="" note={snap.fan_assumption} />
          </section>

          <div className="grid-2">
            <section className="card">
              <h2>{t('campus.topRooms')}</h2>
              {topRooms.length === 0 ? (
                <p className="empty-text">{t('campus.noAlerts')}</p>
              ) : (
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Room</th>
                        <th>{t('campus.actual')}</th>
                        <th>{t('campus.expected')}</th>
                        <th>{t('campus.status')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topRooms.map((r) => (
                        <tr key={r.room_id}>
                          <td>
                            <strong>{r.room_code}</strong>
                          </td>
                          <td>{formatNumber(r.actual_kw, 2)} kW</td>
                          <td>{formatNumber(r.expected_kw, 2)} kW</td>
                          <td className="tone-exceeded">{r.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {topRooms[0]?.reason_explanation && <p className="note-text">{topRooms[0].reason_explanation}</p>}
            </section>

            <section className="card">
              <h2>{t('campus.verified')}</h2>
              {savings.status === 'error' && <ErrorState error={savings.error} onRetry={savings.reload} />}
              {s && (
                <ul className="impact-list">
                  <li>
                    {t('campus.claimed')}: <strong>{formatNumber(s.claimed_kwh, 2)} {t('units2.kwh')}</strong>
                  </li>
                  <li>
                    {t('campus.verifiedLabel')}: <strong>{formatNumber(s.verified_kwh, 2)} {t('units2.kwh')}</strong> · ₹{formatNumber(s.monetary_saving_inr, 2)} · {formatNumber(s.emissions_co2_kg, 2)} {t('units2.kg')} CO₂
                  </li>
                </ul>
              )}
              <p className="note-text">{s?.label}</p>

              <h2 className="section-gap">{t('campus.water')}</h2>
              {alerts.length === 0 ? (
                <p className="empty-text">{t('campus.noAlerts')}</p>
              ) : (
                <ul className="impact-list">
                  {alerts.map((a) => (
                    <li key={a.id}>
                      <strong>{a.location_name}</strong> · {a.status} · {formatDate(a.detected_at, language)} · {formatNumber(a.excess_litres, 0)} L
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </>
  )
}
