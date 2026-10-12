import { Bell } from 'lucide-react'
import StatsStrip from '../../components/student/StatsStrip.jsx'
import ReportForm from '../../components/student/ReportForm.jsx'
import RecentReports from '../../components/student/RecentReports.jsx'
import ImpactPanel from '../../components/student/ImpactPanel.jsx'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getUser } from '../../auth/session.js'
import { getStudentHome } from '../../services/dashboardApi.js'

export default function StudentHome() {
  const { t } = useLanguage()
  const user = getUser()
  const { status, data, error, reload } = useApi(() => getStudentHome(user), [])

  const name = data?.name || user?.name || ''

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('student.welcome', { name })}</h1>
          <p>{t('student.subtitle')}</p>
          {data?.is_simulated && <span className="sim-pill">{t('shell.simulated')}</span>}
        </div>
        <div className="toolbar">
          <button type="button" className="icon-btn icon-btn--round" aria-label={t('shell.notifications')}>
            <Bell size={20} />
          </button>
          <span className="user-avatar user-avatar--lg" aria-hidden="true">
            {name.charAt(0).toUpperCase()}
          </span>
        </div>
      </header>

      {status === 'error' && <ErrorState error={error} onRetry={reload} />}

      {status === 'loading' && !data && (
        <div aria-busy="true">
          <Skeleton height={90} radius={14} />
          <div className="grid-student" style={{ marginTop: 20 }}>
            <Skeleton height={560} radius={14} />
            <Skeleton height={560} radius={14} />
          </div>
        </div>
      )}

      {data && (
        <>
          <StatsStrip stats={data.stats} />
          <div className="grid-student">
            <ReportForm onSubmitted={reload} />
            <div className="stack">
              <RecentReports reports={data.recent} />
              <ImpactPanel impact={data.impact} />
            </div>
          </div>
        </>
      )}
    </>
  )
}
