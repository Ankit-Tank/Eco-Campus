import { Leaf, Zap, Droplet, Trash2 } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext.jsx'

// The backend sends a "key" for each card. This picks the icon and colour for that key.
const CARD_STYLES = {
  carbon: { Icon: Leaf, tone: 'green' },
  electricity: { Icon: Zap, tone: 'amber' },
  water: { Icon: Droplet, tone: 'water' },
  waste: { Icon: Trash2, tone: 'green' },
}

const formatNumber = (n) => n.toLocaleString('en-IN')

// card = { key, value, unit, change_pct, equivalent_value }
// The text (label, caption, unit name) comes from src/i18n, so it changes with the language.
export default function ImpactCard({ card, loading = false }) {
  const { t } = useLanguage()

  if (loading) {
    return (
      <div className="impact-card impact-card--loading" aria-hidden="true">
        <div className="impact-icon" />
        <div className="impact-body">
          <span className="skeleton-line skeleton-line--short" />
          <span className="skeleton-line skeleton-line--tall" />
          <span className="skeleton-line" />
        </div>
      </div>
    )
  }

  const { Icon, tone } = CARD_STYLES[card.key] || CARD_STYLES.carbon
  const hasTrend = typeof card.change_pct === 'number'
  const isUp = card.change_pct >= 0
  const caption = t(`impact.${card.key}.caption`, {
    value: typeof card.equivalent_value === 'number' ? formatNumber(card.equivalent_value) : '',
  })

  return (
    <div className="impact-card">
      <div className={`impact-icon impact-icon--${tone}`}>
        <Icon size={28} />
      </div>
      <div className="impact-body">
        <p className="impact-label">{t(`impact.${card.key}.label`)}</p>
        <div className="impact-figure">
          <span className="impact-value">
            {formatNumber(card.value)} {t(`units.${card.unit}`)}
          </span>
          {hasTrend && (
            <span className={`impact-trend ${isUp ? 'impact-trend--up' : 'impact-trend--down'}`}>
              <span aria-hidden="true">{isUp ? '▲' : '▼'}</span> {Math.abs(card.change_pct)}%
              <span className="visually-hidden"> {t(isUp ? 'impact.increase' : 'impact.decrease')}</span>
            </span>
          )}
        </div>
        <p className="impact-caption">{caption}</p>
      </div>
    </div>
  )
}
