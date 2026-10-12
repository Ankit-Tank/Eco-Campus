import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { formatNumber } from '../../utils/format.js'

// stats = { reports_filed, accepted, in_progress, estimated_saving_kwh }
export default function StatsStrip({ stats }) {
  const { t } = useLanguage()
  const pct = stats.reports_filed ? Math.round((stats.accepted / stats.reports_filed) * 100) : 0

  return (
    <section className="kpi-strip kpi-strip--4">
      <div className="kpi">
        <p className="kpi-label">{t('student.stats.filed')}</p>
        <div className="kpi-value"><strong>{formatNumber(stats.reports_filed)}</strong></div>
        <p className="kpi-note">{t('student.stats.filedNote')}</p>
      </div>
      <div className="kpi">
        <p className="kpi-label">{t('student.stats.accepted')}</p>
        <div className="kpi-value"><strong>{formatNumber(stats.accepted)}</strong></div>
        <p className="kpi-note">{t('student.stats.acceptedNote', { pct })}</p>
      </div>
      <div className="kpi">
        <p className="kpi-label">{t('student.stats.inProgress')}</p>
        <div className="kpi-value"><strong>{formatNumber(stats.in_progress)}</strong></div>
        <p className="kpi-note">{t('student.stats.inProgressNote')}</p>
      </div>
      <div className="kpi">
        <p className="kpi-label">{t('student.stats.impact')}</p>
        <div className="kpi-value">
          <strong>~{formatNumber(stats.estimated_saving_kwh)} {t('units.kwh')}</strong>
        </div>
        <p className="kpi-note">{t('student.stats.impactNote')}</p>
      </div>
    </section>
  )
}
