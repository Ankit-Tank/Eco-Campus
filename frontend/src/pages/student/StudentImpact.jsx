import ImpactPanel from '../../components/student/ImpactPanel.jsx'
import StatsStrip from '../../components/student/StatsStrip.jsx'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getUser } from '../../auth/session.js'
import { getStudentHome } from '../../services/dashboardApi.js'

export default function StudentImpact() {
  const { t } = useLanguage()
  const { status, data, error, reload } = useApi(() => getStudentHome(getUser()), [])

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('student.impactPage.title')}</h1>
          <p>{t('student.impactPage.subtitle')}</p>
          {data?.is_simulated && <span className="sim-pill">{t('shell.simulated')}</span>}
        </div>
      </header>

      {status === 'error' && <ErrorState error={error} onRetry={reload} />}
      {status === 'loading' && <Skeleton height={320} radius={14} />}

      {data && (
        <>
          <StatsStrip stats={data.stats} />
          <div className="grid-2 grid-2--even">
            <ImpactPanel impact={data.impact} showNote />
            <section className="card">
              <h2>{t('student.impactPage.aboutTitle')}</h2>
              <p className="card-sub">{t('student.impactPage.aboutText')}</p>
            </section>
          </div>
        </>
      )}
    </>
  )
}
