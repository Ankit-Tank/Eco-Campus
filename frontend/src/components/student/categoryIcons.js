import { Droplet, Lightbulb, Wind, Zap, Wrench, Waves, HelpCircle } from 'lucide-react'

// Icon shown when a report has no photo. Keys = issue types (see "issueTypes" in src/i18n).
export const CATEGORY_ICONS = {
  leaking_tap: Droplet,
  broken_pipe: Wrench,
  overflowing_tank: Waves,
  low_pressure: Droplet,
  water_wastage: Droplet,
  lights_left_on: Lightbulb,
  ac_running: Wind,
  electrical_damage: Zap,
  other: HelpCircle,
}

export const ISSUE_TYPES = Object.keys(CATEGORY_ICONS)
