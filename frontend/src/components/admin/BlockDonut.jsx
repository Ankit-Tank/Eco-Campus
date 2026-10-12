import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { formatNumber } from '../../utils/format.js'

const COLORS = ['#3fbf74', '#3aa8ff', '#fbbf24', '#f97316', '#a56be0', '#f4a3c4', '#c9ced8']

// blocks = [{ key, name, share_pct, kwh }]
export default function BlockDonut({ blocks, totalKwh }) {
  const { t } = useLanguage()

  return (
    <div className="donut-wrap">
      <div className="donut" role="img" aria-label={t('admin.blocks.title')}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={blocks} dataKey="kwh" nameKey="name" innerRadius="66%" outerRadius="100%" paddingAngle={1} stroke="none">
              {blocks.map((b, i) => (
                <Cell key={b.key} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => `${formatNumber(value)} kWh`} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <span>{t('admin.blocks.total')}</span>
          <strong>
            {formatNumber(totalKwh)} {t('units.kwh')}
          </strong>
        </div>
      </div>

      <ul className="donut-legend">
        {blocks.map((b, i) => (
          <li key={b.key}>
            <i style={{ background: COLORS[i % COLORS.length] }} />
            <span>{b.name}</span>
            <strong>{b.share_pct}%</strong>
          </li>
        ))}
      </ul>
    </div>
  )
}
