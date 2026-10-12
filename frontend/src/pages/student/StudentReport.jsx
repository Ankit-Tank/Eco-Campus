import { useNavigate } from 'react-router-dom'
import ReportForm from '../../components/student/ReportForm.jsx'
import { useLanguage } from '../../i18n/LanguageContext.jsx'

export default function StudentReport() {
  const { t } = useLanguage()
  const navigate = useNavigate()
  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('student.reportPage.title')}</h1>
          <p>{t('student.reportPage.subtitle')}</p>
        </div>
      </header>
      <div className="narrow">
        {/* After sending, go to the list so the student sees the new report with its status. */}
        <ReportForm onSubmitted={() => setTimeout(() => navigate('/student/my-reports'), 1200)} />
      </div>
    </>
  )
}
