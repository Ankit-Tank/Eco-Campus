import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'

// Password box with a show/hide button.
export default function PasswordField({ id, label, value, onChange, autoComplete }) {
  const { t } = useLanguage()
  const [visible, setVisible] = useState(false)

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="password-wrap">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible(!visible)}
          aria-label={t(visible ? 'auth.hidePassword' : 'auth.showPassword')}
        >
          {visible ? <EyeOff size={20} /> : <Eye size={20} />}
        </button>
      </div>
    </div>
  )
}
