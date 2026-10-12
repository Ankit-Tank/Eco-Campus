import { useEffect, useRef, useState } from 'react'
import { Bot, RotateCcw, SendHorizontal, User } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { askAssistant } from '../../services/assistantApi.js'
import { getErrorMessage } from '../../utils/errors.js'

// Messages live in this component only. Leaving the page starts a fresh chat.
export default function StudentChat() {
  const { t } = useLanguage()
  const [messages, setMessages] = useState([]) // { id, role: 'user' | 'assistant', text, error? }
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [simulated, setSimulated] = useState(false)
  const bottom = useRef(null)
  const nextId = useRef(1)

  // Keep the newest message in view.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, sending])

  async function send(text) {
    const question = text.trim()
    if (!question || sending) return
    setMessages((m) => [...m, { id: nextId.current++, role: 'user', text: question }])
    setInput('')
    setSending(true)
    try {
      const reply = await askAssistant(question)
      setSimulated(Boolean(reply.is_simulated))
      setMessages((m) => [...m, { id: nextId.current++, role: 'assistant', text: reply.answer }])
    } catch (error) {
      // The assistant failing must never break the app, so we show a plain message in the chat.
      const text = error.code === 'NETWORK' ? getErrorMessage(error, t) : t('student.chat.unavailable')
      setMessages((m) => [...m, { id: nextId.current++, role: 'assistant', text, error: true }])
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  const suggestions = t('student.chat.suggestions')
  const suggestionList = Array.isArray(suggestions) ? suggestions : []

  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t('student.chat.title')}</h1>
          <p>{t('student.chat.subtitle')}</p>
        </div>
        {messages.length > 0 && (
          <button type="button" className="btn btn--outline" onClick={() => setMessages([])} disabled={sending}>
            <RotateCcw size={16} aria-hidden="true" /> {t('student.chat.newChat')}
          </button>
        )}
      </header>

      <section className="chat card">
        <div className="chat-log" role="log" aria-live="polite" aria-label={t('student.chat.title')}>
          <div className="msg msg--assistant">
            <span className="msg-avatar" aria-hidden="true"><Bot size={18} /></span>
            <div className="msg-bubble">{t('student.chat.welcome')}</div>
          </div>

          {messages.length === 0 && suggestionList.length > 0 && (
            <div className="chat-suggest">
              <p>{t('student.chat.suggestionsTitle')}</p>
              <div className="chips">
                {suggestionList.map((s) => (
                  <button key={s} type="button" className="chip chip--plain" onClick={() => send(s)} disabled={sending}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className={`msg msg--${m.role} ${m.error ? 'msg--error' : ''}`}>
              <span className="msg-avatar" aria-hidden="true">
                {m.role === 'user' ? <User size={18} /> : <Bot size={18} />}
              </span>
              <div className="msg-bubble">
                <span className="visually-hidden">{m.role === 'user' ? t('student.chat.you') : t('student.chat.assistant')}: </span>
                {m.text}
              </div>
            </div>
          ))}

          {sending && (
            <div className="msg msg--assistant" aria-label={t('student.chat.thinking')}>
              <span className="msg-avatar" aria-hidden="true"><Bot size={18} /></span>
              <div className="msg-bubble typing" aria-hidden="true"><i /><i /><i /></div>
            </div>
          )}
          <div ref={bottom} />
        </div>

        <form
          className="chat-input"
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
        >
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('student.chat.placeholder')}
            aria-label={t('student.chat.placeholder')}
            maxLength={1000}
          />
          <button type="submit" className="btn btn--primary chat-send" disabled={sending || !input.trim()} aria-label={t('student.chat.send')}>
            <SendHorizontal size={18} aria-hidden="true" />
          </button>
        </form>

        <p className="note-text chat-note">
          {t('student.chat.note')} {simulated && <span className="sim-pill sim-pill--inline">{t('shell.simulated')}</span>}
        </p>
      </section>
    </>
  )
}
