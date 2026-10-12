import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { formatNumber } from '../../utils/format.js'

// buildings = [{ name, active_kw, daily_var_pct, status: 'exceeded' | 'normal' | 'below' }]
export default function BuildingTable({ buildings }) {
  const { t } = useLanguage()

  if (buildings.length === 0) return <p className="empty-text">{t('admin.buildings.empty')}</p>

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>{t('admin.buildings.name')}</th>
            <th>{t('admin.buildings.active')}</th>
            <th>{t('admin.buildings.daily')}</th>
            <th>{t('admin.buildings.insight')}</th>
          </tr>
        </thead>
        <tbody>
          {buildings.map((b) => (
            <tr key={b.name}>
              <td>{b.name}</td>
              <td>{formatNumber(b.active_kw)} {t('units2.kw')}</td>
              <td className={`tone-${b.status}`}>
                {b.daily_var_pct > 0 ? '+' : ''}
                {b.daily_var_pct}%
              </td>
              <td className={`tone-${b.status}`}>{t(`admin.insight.${b.status}`)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
