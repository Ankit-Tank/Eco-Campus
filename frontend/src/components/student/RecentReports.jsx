import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import ReportThumb from './ReportThumb.jsx'
import StatusBadge from '../ui/StatusBadge.jsx'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { formatDate } from '../../utils/format.js'

// One row per report. Used on Home (latest 5) and on the My Reports page (all).
export function ReportRow({ report }) {
  const { language } = useLanguage()
  return (
    <li className="report-row">
      <ReportThumb report={report} />
      <div className="report-text">
        <strong>{report.title}</strong>
        <span>
          {report.place} · {formatDate(report.created_at, language)}
        </span>
      </div>
      <StatusBadge status={report.status} />
    </li>
  )
}

export default function RecentReports({ reports }) {
  const { t } = useLanguage()
  return (
    <section className="card">
      <div className="card-head">
        <h2>{t('student.recent.title')}</h2>
        <Link to="/student/my-reports" className="link-arrow">
          {t('common.viewAll')} <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </div>
      {reports.length === 0 ? (
        <p className="empty-text">{t('student.recent.empty')}</p>
      ) : (
        <ul className="report-list">
          {reports.map((r) => (
            <ReportRow key={r.id} report={r} />
          ))}
        </ul>
      )}
    </section>
  )
}
