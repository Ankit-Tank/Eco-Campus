import { Home, PlusCircle, FileText, BarChart3, Zap, Droplet, Bell, Wrench } from 'lucide-react'

// Sidebar menus. "label" is a key in src/i18n. A "group" has a heading you can open or close.
// Keep the "to" paths in sync with src/App.jsx.
export const ADMIN_NAV = [
  { to: '/admin/overview', label: 'adminNav.overview', Icon: Home },
  {
    group: 'adminNav.resources',
    items: [
      { to: '/admin/electricity', label: 'adminNav.electricity', Icon: Zap },
      { to: '/admin/water', label: 'adminNav.water', Icon: Droplet },
    ],
  },
  {
    group: 'adminNav.operations',
    items: [
      { to: '/admin/alerts', label: 'adminNav.alerts', Icon: Bell },
      { to: '/admin/maintenance', label: 'adminNav.maintenance', Icon: Wrench },
    ],
  },
  { to: '/admin/reports', label: 'adminNav.reports', Icon: FileText },
]

export const STUDENT_NAV = [
  { to: '/student/home', label: 'studentNav.home', Icon: Home },
  { to: '/student/report', label: 'studentNav.reportIssue', Icon: PlusCircle },
  { to: '/student/my-reports', label: 'studentNav.myReports', Icon: FileText },
  { to: '/student/impact', label: 'studentNav.impact', Icon: BarChart3 },
]
