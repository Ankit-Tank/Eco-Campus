import { useLanguage } from '../../i18n/LanguageContext.jsx'

// Complaint status as coloured text. Keys: submitted, accepted, in_progress, resolved, rejected, reopened
// The words come from src/i18n ("status.*"). Keep the keys in sync with backend/app/routes/complaints.py
export default function StatusBadge({ status }) {
  const { t } = useLanguage()
  return <span className={`status status--${status}`}>{t(`status.${status}`)}</span>
}
