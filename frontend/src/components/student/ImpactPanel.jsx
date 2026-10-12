import { Droplet, Leaf, Zap } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { formatNumber } from '../../utils/format.js'

// impact = { electricity_kwh, water_litres, co2_kg }
export default function ImpactPanel({ impact, showNote = false }) {
  const { t } = useLanguage()
  const rows = [
    { key: 'electricity', Icon: Zap, tone: 'amber', value: impact.electricity_kwh, unit: t('units.kwh') },
    { key: 'water', Icon: Droplet, tone: 'water', value: impact.water_litres, unit: t('units.litres') },
    { key: 'co2', Icon: Leaf, tone: 'green', value: impact.co2_kg, unit: t('units.kg') },
  ]

  return (
    <section className="card">
      <h2>{t('student.impactPanel.title')}</h2>
      <p className="card-sub">{t('student.impactPanel.subtitle')}</p>
      <ul className="impact-list">
        {rows.map(({ key, Icon, tone, value, unit }) => (
          <li key={key}>
            <span className={`impact-dot impact-dot--${tone}`} aria-hidden="true">
              <Icon size={20} />
            </span>
            <span className="impact-name">{t(`student.impactPanel.${key}`)}</span>
            <strong>
              {formatNumber(value)} {unit}
            </strong>
          </li>
        ))}
      </ul>
      {showNote && <p className="note-text">{t('student.impactPanel.estimateNote')}</p>}
    </section>
  )
}
