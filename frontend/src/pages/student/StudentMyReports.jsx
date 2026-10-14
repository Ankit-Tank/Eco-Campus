import { useState } from 'react'
import { ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'
import ReportThumb from '../../components/student/ReportThumb.jsx'
import StatusBadge from '../../components/ui/StatusBadge.jsx'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'
import { useApi } from '../../hooks/useApi.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getMyComplaints, reopenComplaint } from '../../services/complaintsApi.js'
import { getErrorMessage } from '../../utils/errors.js'
import { formatDate } from '../../utils/format.js'

// These are the statuses the backend really uses (see backend/app/routes/complaints.py).
const FILTERS = ['all', 'submitted', 'acknowledged', 'assigned', 'in_progress', 'resolved', 'reopened']

// One report: tap to see its photo, notes and the full status history.
function ReportItem({ report, onChanged }) {
  const { t, language } = useLanguage()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null)
  const panelId = `report-detail-${report.id}`
  // The first line of the stored text is the title; anything after it is the longer description.
  const details = (report.description || '').split('\n').slice(1).join('\n').trim()

  async function reopen() {
    setBusy(true)
    setMessage(null)
    try {
      await reopenComplaint(report.id, reason.trim())
      setReason('')
      setMessage({ type: 'success', text: t('student.myReports.reopenDone') })
      onChanged()
    } catch (error) {
      setMessage({ type: 'error', text: getErrorMessage(error, t) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="report-item">
      <button type="button" className="report-row report-row--button" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(!open)}>
        <ReportThumb report={report} />
        <div className="report-text">
          <strong>{report.title}</strong>
          <span>
            {report.complaint_code ? `${report.complaint_code} · ` : ''}
            {report.place} · {formatDate(report.created_at, language)}
          </span>
        </div>
        <StatusBadge status={report.status} />
        {open ? <ChevronUp size={18} aria-hidden="true" /> : <ChevronDown size={18} aria-hidden="true" />}
      </button>

      {open && (
        <div className="report-detail" id={panelId}>
          {report.image_url && <img className="report-detail-photo" src={report.image_url} alt={t('student.myReports.photo')} />}
          {details && <p className="report-detail-desc">{details}</p>}
          {report.assigned_to_email && (
            <p className="note-text">
              {t('student.myReports.assigned')}: {report.assigned_to_email}
            </p>
          )}
          {report.resolution_notes && <p className="note-text">{report.resolution_notes}</p>}

          <h3 className="report-detail-head">{t('student.myReports.history')}</h3>
          {(report.history || []).length === 0 ? (
            <p className="note-text">{t('student.myReports.loadHistory')}</p>
          ) : (
            <ol className="timeline">
              {report.history.map((h) => (
                <li key={h.id}>
                  <StatusBadge status={h.new_status} />
                  <span className="timeline-when">{formatDate(h.changed_at, language)}</span>
                  {h.note && <span className="timeline-note">{h.note}</span>}
                </li>
              ))}
            </ol>
          )}

          {report.status === 'resolved' && (
            <div className="form" style={{ marginTop: 12 }}>
              <div className="field">
                <label htmlFor={`reopen-${report.id}`}>{t('student.myReports.reopenReason')}</label>
                <textarea id={`reopen-${report.id}`} rows={2} maxLength={300} value={reason} onChange={(e) => setReason(e.target.value)} />
              </div>
              <button type="button" className="btn btn--outline" disabled={busy} onClick={reopen}>
                <RotateCcw size={16} aria-hidden="true" /> {t('student.myReports.reopen')}
              </button>
            </div>
          )}
          {message && (
            <p className={message.type === 'success' ? 'note-text' : 'field-error'} role="status">
              {message.text}
            </p>
          )}
        </div>
      )}
    </li>
  )
}

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
                <ReportItem key={r.id} report={r} onChanged={reload} />
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  )
}
