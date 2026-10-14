import { Droplet, Lightbulb, Wind, Zap, Wrench, Waves, HelpCircle } from 'lucide-react'

// Issue types a student can pick in the report form. Keys = "issueTypes" in src/i18n.
const FORM_ICONS = {
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

// Icon shown when a report has no photo. Also covers categories the backend stores that are not
// in the form: "general_wastage" (the stored name of water_wastage) and "appliance_left_on"
// (created by the one-tap "appliance left on" signal on the home page).
export const CATEGORY_ICONS = {
  ...FORM_ICONS,
  general_wastage: Droplet,
  appliance_left_on: Zap,
}

export const ISSUE_TYPES = Object.keys(FORM_ICONS)
