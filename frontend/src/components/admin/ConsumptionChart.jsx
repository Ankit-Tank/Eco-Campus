import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { formatNumber, formatShortDate } from '../../utils/format.js'

const ACTUAL = '#1e3a8a'
const BASELINE = '#9aa5b5'

// series = [{ date, actual_kw, baseline_kw }]   events = [{ date }]
export default function ConsumptionChart({ series, events }) {
  const { t, language } = useLanguage()
  const data = series.map((p) => ({ ...p, label: formatShortDate(p.date, language) }))

  return (
    <>
      <div className="chart-box" role="img" aria-label={t('admin.telemetry.title')}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#e8edf3" />
            <XAxis dataKey="label" tickLine={false} axisLine={{ stroke: '#cfd6df' }} tick={{ fontSize: 12, fill: '#5f6b7a' }} />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fill: '#5f6b7a' }}
              tickFormatter={(v) => formatNumber(v)}
              label={{ value: t('admin.telemetry.yAxis'), angle: -90, position: 'insideLeft', style: { fontSize: 12, fill: '#5f6b7a' } }}
            />
            <Tooltip formatter={(value) => `${formatNumber(value)} kW`} />
            <Line type="monotone" dataKey="baseline_kw" name={t('admin.telemetry.baseline')} stroke={BASELINE} strokeWidth={2} strokeDasharray="6 5" dot={false} />
            <Line type="monotone" dataKey="actual_kw" name={t('admin.telemetry.actual')} stroke={ACTUAL} strokeWidth={2.5} dot={false} />
            {events.map((event) => {
              const point = data.find((p) => p.date === event.date)
              return point ? <ReferenceDot key={event.date} x={point.label} y={point.actual_kw} r={5} fill={ACTUAL} stroke="#fff" strokeWidth={2} /> : null
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <ul className="chart-legend">
        <li>
          <i className="legend-line" style={{ background: ACTUAL }} /> {t('admin.telemetry.actual')}
        </li>
        <li>
          <i className="legend-line legend-line--dashed" style={{ borderColor: BASELINE }} /> {t('admin.telemetry.baseline')}
        </li>
        <li>
          <i className="legend-dot" style={{ background: ACTUAL }} /> {t('admin.telemetry.event')}
        </li>
      </ul>
    </>
  )
}
