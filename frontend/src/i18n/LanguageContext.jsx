import { createContext, useContext, useEffect, useState } from 'react'
import en from './en.js'
import hi from './hi.js'
import { STORAGE_KEYS } from '../config.js'

const translations = { en, hi }

// Finds "auth.sendOtp" inside the dictionary.
function lookup(dictionary, key) {
  return key.split('.').reduce((part, name) => (part ? part[name] : undefined), dictionary)
}

function getSavedLanguage() {
  const saved = localStorage.getItem(STORAGE_KEYS.language)
  return saved === 'hi' || saved === 'en' ? saved : 'en' // English is the default
}

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(getSavedLanguage)

  // Save the choice. It stays after login, logout and page refresh.
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.language, language)
    document.documentElement.lang = language
  }, [language])

  // t('auth.otpSentTo', { phone: '...' }) gives the text in the current language.
  function t(key, values = {}) {
    let text = lookup(translations[language], key) ?? lookup(translations.en, key) ?? key
    Object.entries(values).forEach(([name, value]) => {
      text = text.replaceAll(`{${name}}`, String(value))
    })
    return text
  }

  return <LanguageContext.Provider value={{ language, setLanguage, t }}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  return useContext(LanguageContext)
}
