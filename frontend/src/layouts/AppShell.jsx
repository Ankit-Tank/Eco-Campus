import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, Menu, User, X } from 'lucide-react'
import Brand from '../components/Brand.jsx'
import LanguageToggle from '../components/LanguageToggle.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { getUser, logout } from '../auth/session.js'
import { ADMIN_NAV, STUDENT_NAV } from './nav.js'
import '../styles/app.css'

function NavItem({ item, t, onNavigate }) {
  const { Icon } = item
  return (
    <NavLink to={item.to} className="nav-item" onClick={onNavigate}>
      <Icon size={20} aria-hidden="true" />
      <span>{t(item.label)}</span>
    </NavLink>
  )
}

function NavGroup({ group, items, t, onNavigate }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="nav-group">
      <button type="button" className="nav-group-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span>{t(group)}</span>
        <ChevronDown size={18} className={open ? '' : 'is-closed'} aria-hidden="true" />
      </button>
      {open && items.map((item) => <NavItem key={item.to} item={item} t={t} onNavigate={onNavigate} />)}
    </div>
  )
}

// Sidebar + page area. "variant" is "admin" or "student". Pages render inside <Outlet />.
export default function AppShell({ variant }) {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const user = getUser()
  const [menuOpen, setMenuOpen] = useState(false)
  const nav = variant === 'admin' ? ADMIN_NAV : STUDENT_NAV

  // Close the mobile menu after moving to another page.
  useEffect(() => setMenuOpen(false), [location.pathname])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className={`shell shell--${variant}`}>
      <header className="mobile-bar">
        <button type="button" className="icon-btn" aria-label={t('shell.openMenu')} onClick={() => setMenuOpen(true)}>
          <Menu size={22} />
        </button>
        <Brand />
      </header>

      {menuOpen && <div className="scrim" onClick={() => setMenuOpen(false)} aria-hidden="true" />}

      <aside className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
        <div className="sidebar-top">
          <Brand />
          <button type="button" className="icon-btn sidebar-close" aria-label={t('shell.closeMenu')} onClick={() => setMenuOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label={t('shell.mainNav')}>
          {nav.map((entry) =>
            entry.group ? (
              <NavGroup key={entry.group} group={entry.group} items={entry.items} t={t} onNavigate={() => setMenuOpen(false)} />
            ) : (
              <NavItem key={entry.to} item={entry} t={t} onNavigate={() => setMenuOpen(false)} />
            )
          )}
        </nav>

        <div className="sidebar-foot">
          <LanguageToggle />
          <div className="user-row">
            <span className="user-avatar" aria-hidden="true">
              {user?.name ? user.name.charAt(0).toUpperCase() : <User size={18} />}
            </span>
            <div className="user-text">
              <strong>{user?.name}</strong>
              <span>{variant === 'admin' ? `• ${t('roles.admin')}` : t('roles.student')}</span>
            </div>
            <button type="button" className="icon-btn" aria-label={t('shell.logout')} title={t('shell.logout')} onClick={handleLogout}>
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      <main className="page">
        <Outlet />
      </main>
    </div>
  )
}
