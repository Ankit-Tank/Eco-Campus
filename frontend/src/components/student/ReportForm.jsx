import { useRef, useState } from 'react'
import { ArrowRight, ChevronDown, ImageIcon, X } from 'lucide-react'
import { ISSUE_TYPES } from './categoryIcons.js'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { createComplaint } from '../../services/complaintsApi.js'
import { getErrorMessage } from '../../utils/errors.js'

const MAX_DESCRIPTION = 500
const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const IMAGE_TYPES = ['image/jpeg', 'image/png']

const EMPTY = { title: '', category: '', place: '', description: '' }

// "onSubmitted" runs after the backend saved the report, so the page can refresh its lists.
export default function ReportForm({ onSubmitted }) {
  const { t } = useLanguage()
  const [values, setValues] = useState(EMPTY)
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState('')
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState(null) // { type: 'success' | 'error', text }
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef(null)

  const setField = (name) => (e) => {
    setValues({ ...values, [name]: e.target.value })
    setErrors({ ...errors, [name]: undefined })
  }

  function pickImage(file) {
    if (!file) return
    if (!IMAGE_TYPES.includes(file.type)) return setErrors({ ...errors, image: t('student.form.errImageType') })
    if (file.size > MAX_IMAGE_BYTES) return setErrors({ ...errors, image: t('student.form.errImageSize') })
    if (preview) URL.revokeObjectURL(preview)
    setImage(file)
    setPreview(URL.createObjectURL(file))
    setErrors({ ...errors, image: undefined })
  }

  function removeImage() {
    if (preview) URL.revokeObjectURL(preview)
    setImage(null)
    setPreview('')
    if (fileInput.current) fileInput.current.value = ''
  }

  function validate() {
    const found = {}
    if (!values.title.trim()) found.title = t('student.form.errTitle')
    if (!values.category) found.category = t('student.form.errType')
    if (!values.place.trim()) found.place = t('student.form.errPlace')
    return found
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setMessage(null)
    const found = validate()
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setSubmitting(true)
    try {
      await createComplaint({
        title: values.title.trim(),
        category: values.category,
        location: values.place.trim(),
        description: values.description.trim(),
        image,
      })
      setValues(EMPTY)
      removeImage()
      setMessage({ type: 'success', text: t('student.form.success') })
      onSubmitted?.()
    } catch (error) {
      setMessage({ type: 'error', text: getErrorMessage(error, t) })
    } finally {
      setSubmitting(false)
    }
  }

  const star = <span className="req" aria-hidden="true"> *</span>

  return (
    <section className="card">
      <h2>{t('student.form.title')}</h2>
      <p className="card-sub">{t('student.form.subtitle')}</p>

      <form className="form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="rf-title">{t('student.form.fieldTitle')}{star}</label>
          <input id="rf-title" value={values.title} onChange={setField('title')} placeholder={t('student.form.titlePlaceholder')} maxLength={120} aria-invalid={!!errors.title} />
          {errors.title && <p className="field-error">{errors.title}</p>}
        </div>

        <div className="field-row">
          <div className="field">
            <label htmlFor="rf-type">{t('student.form.issueType')}{star}</label>
            <div className="select-field">
              <select id="rf-type" value={values.category} onChange={setField('category')} aria-invalid={!!errors.category} className={values.category ? '' : 'is-placeholder'}>
                <option value="">{t('student.form.selectType')}</option>
                {ISSUE_TYPES.map((key) => (
                  <option key={key} value={key}>
                    {t(`issueTypes.${key}`)}
                  </option>
                ))}
              </select>
              <ChevronDown size={16} aria-hidden="true" />
            </div>
            {errors.category && <p className="field-error">{errors.category}</p>}
          </div>

          <div className="field">
            <label htmlFor="rf-place">{t('student.form.place')}{star}</label>
            <input id="rf-place" value={values.place} onChange={setField('place')} placeholder={t('student.form.placePlaceholder')} maxLength={120} aria-invalid={!!errors.place} />
            {errors.place && <p className="field-error">{errors.place}</p>}
          </div>
        </div>

        <div className="field">
          <label htmlFor="rf-desc">{t('student.form.description')}</label>
          <textarea id="rf-desc" rows={4} value={values.description} onChange={setField('description')} placeholder={t('student.form.descriptionPlaceholder')} maxLength={MAX_DESCRIPTION} />
          <p className="counter">{values.description.length}/{MAX_DESCRIPTION}</p>
        </div>

        <div className="field">
          <span className="label">
            {t('student.form.uploadImage')} <span className="muted">{t('student.form.optional')}</span>
          </span>

          {preview ? (
            <div className="upload-preview">
              <img src={preview} alt="" />
              <span>{image.name}</span>
              <button type="button" className="icon-btn" onClick={removeImage} aria-label={t('student.form.removeImage')}>
                <X size={18} />
              </button>
            </div>
          ) : (
            <div
              className={`dropzone ${dragging ? 'is-dragging' : ''}`}
              onDragOver={(e) => {
                e.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragging(false)
                pickImage(e.dataTransfer.files?.[0])
              }}
            >
              <ImageIcon size={26} aria-hidden="true" />
              <p>{t('student.form.dropHere')}</p>
              <p>
                {t('student.form.or')}{' '}
                <button type="button" className="link-btn" onClick={() => fileInput.current?.click()}>
                  {t('student.form.browse')}
                </button>
              </p>
              <small>{t('student.form.supports')}</small>
            </div>
          )}
          <input ref={fileInput} type="file" accept="image/jpeg,image/png" hidden onChange={(e) => pickImage(e.target.files?.[0])} />
          {errors.image && <p className="field-error">{errors.image}</p>}
        </div>

        {message && (
          <p className={`form-message form-message--${message.type}`} role={message.type === 'error' ? 'alert' : 'status'}>
            {message.text}
          </p>
        )}

        <button type="submit" className="btn btn--primary" disabled={submitting}>
          {submitting ? t('student.form.submitting') : t('student.form.submit')}
          {!submitting && <ArrowRight size={17} aria-hidden="true" />}
        </button>
      </form>
    </section>
  )
}
