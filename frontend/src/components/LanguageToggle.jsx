import { useLanguage } from '../i18n/LanguageContext.jsx'

// Each language is always written in its own language, so people can find theirs.
const OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'हिन्दी' },
]

export default function LanguageToggle() {
  const { language, setLanguage, t } = useLanguage()

  return (
    <div className="language-toggle" role="group" aria-label={t('nav.language')}>
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          lang={option.value}
          aria-pressed={language === option.value}
          onClick={() => setLanguage(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
