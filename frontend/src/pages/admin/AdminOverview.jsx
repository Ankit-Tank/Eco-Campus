import { useMemo, useState } from 'react'
import { Calendar, ChevronDown, Download } from 'lucide-react'
import ConsumptionChart from '../../components/admin/ConsumptionChart.jsx'
import BlockDonut from '../../components/admin/BlockDonut.jsx'
import BuildingTable from '../../components/admin/BuildingTable.jsx'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getAdminOverview } from '../../services/dashboardApi.js'
import { downloadCsv, formatNumber, formatRange, lastDays } from '../../utils/format.js'

const RANGE_OPTIONS = [7, 14, 30]

function Kpi({ label, children, note }) {
  return (
    <div className="kpi">
      <p className="kpi-label">{label}</p>
      <div className="kpi-value">{children}</div>
      {note && <p className="kpi-note">{note}</p>}
    </div>
  )
}

function OverviewSkeleton() {
  return (
    <div aria-busy="true">
      <div className="kpi-strip">
        {[0, 1, 2].map((i) => (
          <div className="kpi" key={i}>
            <Skeleton width={90} />
            <Skeleton height={36} width={150} style={{ marginTop: 10 }} />
          </div>
        ))}
      </div>
      <div className="grid-2">
        <Skeleton height={340} radius={14} />
        <Skeleton height={340} radius={14} />
      </div>
      <Skeleton height={240} radius={14} style={{ marginTop: 20 }} />
    </div>
  )
}

export default function AdminOverview() {
  const { t, language } = useLanguage()
  const [zone, setZone] = useState('all')
  const [days, setDays] = useState(14)
  const range = useMemo(() => lastDays(days), [days])

  // Refreshes quietly every 15 seconds. Real-time (1-2 s) polling can be added later for the Ghost Load page.
  const { status, data, error, reload } = useApi(() => getAdminOverview({ ...range, zone }), [zone, range.from, range.to], { interval: 15000 })

  function handleExport() {
    if (!data) return
    const rows = [
      [t('admin.csv.date'), t('admin.csv.actual'), t('admin.csv.baseline')],
      ...data.series.map((p) => [p.date, p.actual_kw, p.baseline_kw]),
      [],
      [t('admin.buildings.name'), t('admin.buildings.active'), t('admin.buildings.daily'), t('admin.buildings.insight')],
      ...data.buildings.map((b) => [b.name, b.active_kw, b.daily_var_pct, t(`admin.insight.${b.status}`)]),
    ]
    downloadCsv(`${t('admin.csv.file')}-${range.from}_${range.to}.csv`, rows)
  }

  const kpis = data?.kpis
  const down = kpis && kpis.consumption_change_pct <= 0

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('admin.title')}</h1>
          <p>{t('admin.subtitle')}</p>
          {data?.is_simulated && <span className="sim-pill">{t('shell.simulated')}</span>}
        </div>

        <div className="toolbar">
          <label className="select-pill">
            <span className="visually-hidden">{t('common.zone')}</span>
            <select value={zone} onChange={(e) => setZone(e.target.value)}>
              <option value="all">{t('common.allZones')}</option>
              {data?.zones.map((z) => (
                <option key={z.key} value={z.key}>
                  {z.name}
                </option>
              ))}
            </select>
            <ChevronDown size={16} aria-hidden="true" />
          </label>

          <label className="select-pill">
            <span className="visually-hidden">{t('common.dateRange')}</span>
            <Calendar size={16} aria-hidden="true" />
            <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
              {RANGE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {formatRange(lastDays(n).from, lastDays(n).to, language)}
                </option>
              ))}
            </select>
            <ChevronDown size={16} aria-hidden="true" />
          </label>

          <button type="button" className="btn btn--outline" onClick={handleExport} disabled={!data}>
            <Download size={16} aria-hidden="true" /> {t('common.export')}
          </button>
        </div>
      </header>

      {status === 'error' && <ErrorState error={error} onRetry={reload} />}
      {status === 'loading' && !data && <OverviewSkeleton />}

      {data && (
        <>
          <section className="kpi-strip" aria-label={t('admin.title')}>
            <Kpi label={t('admin.kpi.conserved')} note={t('admin.kpi.conservedNote')}>
              <strong>
                {formatNumber(kpis.conserved_mwh, 1)} {t('units2.mwh')}
              </strong>
            </Kpi>
            <Kpi label={t('admin.kpi.consumption')}>
              <strong>
                {formatNumber(kpis.consumption_mwh, 1)} {t('units2.mwh')}
              </strong>
              <span className={`trend ${down ? 'trend--good' : 'trend--bad'}`}>
                <span aria-hidden="true">{down ? '⌄' : '⌃'}</span> {kpis.consumption_change_pct > 0 ? '+' : ''}
                {kpis.consumption_change_pct}%
                <span className="visually-hidden"> {t(down ? 'admin.kpi.lower' : 'admin.kpi.higher')}</span>
              </span>
            </Kpi>
            <Kpi label={t('admin.kpi.co2')}>
              <strong>
                {formatNumber(kpis.co2_saved_tonnes, 1)} {t('units2.tco2e')}
              </strong>
            </Kpi>
          </section>

          <div className="grid-2">
            <section className="card card--chart">
              <h2>{t('admin.telemetry.title')}</h2>
              <p className="card-sub">{t('admin.telemetry.subtitle')}</p>
              <ConsumptionChart series={data.series} events={data.optimization_events} />
            </section>

            <section className="card">
              <h2>{t('admin.blocks.title')}</h2>
              <BlockDonut blocks={data.blocks} totalKwh={data.total_kwh} />
            </section>
          </div>

          <section className="card card--spaced">
            <h2>{t('admin.buildings.title')}</h2>
            <p className="card-sub">{t('admin.buildings.subtitle')}</p>
            <BuildingTable buildings={data.buildings} />
          </section>
        </>
      )}
    </>
  )
}
