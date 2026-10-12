import { CATEGORY_ICONS } from './categoryIcons.js'

// The report photo, or an icon for the issue type when there is no photo.
export default function ReportThumb({ report }) {
  const Icon = CATEGORY_ICONS[report.category] || CATEGORY_ICONS.other
  if (report.image_url) return <img className="thumb" src={report.image_url} alt="" />
  return (
    <span className="thumb thumb--icon" aria-hidden="true">
      <Icon size={22} />
    </span>
  )
}
