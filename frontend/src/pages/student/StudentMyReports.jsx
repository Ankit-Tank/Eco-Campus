import { useState } from 'react'
import { ReportRow } from '../../components/student/RecentReports.jsx'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getMyComplaints } from '../../services/complaintsApi.js'

const FILTERS = ['all', 'submitted', 'accepted', 'in_progress', 'resolved', 'rejected']

export default function StudentMyReports() {
  const { t } = useLanguage()
  const [filter, setFilter] = useState('all')
  const { status, data, error, reload } = useApi(() => getMyComplaints(), [])

  const items = data ? data.items.filter((r) => filter === 'all' || r.status === filter) : []

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('student.myReports.title')}</h1>
          <p>{t('student.myReports.subtitle')}</p>
        </div>
      </header>

      <div className="chips" role="group" aria-label={t('student.myReports.title')}>
        {FILTERS.map((f) => (
          <button key={f} type="button" className="chip" aria-pressed={filter === f} onClick={() => setFilter(f)}>
            {f === 'all' ? t('student.myReports.all') : t(`status.${f}`)}
          </button>
        ))}
      </div>

      {status === 'error' && <ErrorState error={error} onRetry={reload} />}
      {status === 'loading' && <Skeleton height={300} radius={14} />}

      {data && (
        <section className="card">
          {items.length === 0 ? (
            <p className="empty-text">{t('student.myReports.empty')}</p>
          ) : (
            <ul className="report-list">
              {items.map((r) => (
                <ReportRow key={r.id} report={r} />
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  )
}
