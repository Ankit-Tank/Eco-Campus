import { useEffect, useState } from 'react'
import {
  CheckCircle,
  HelpCircle,
  Loader2,
  RefreshCw,
  Save,
  Settings as SettingsIcon,
  Sliders,
} from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getSettings, updateSettings } from '../../services/settingsApi.js'
import ErrorState from '../../components/ui/ErrorState.jsx'
import Skeleton from '../../components/ui/Skeleton.jsx'

export default function AdminSettings() {
  const { t } = useLanguage()
  const [settings, setSettings] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState('')

  async function loadData() {
    setError(null)
    setLoading(true)
    try {
      const res = await getSettings()
      setSettings(res.settings || {})
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleChange = (key) => (e) => {
    setSettings({ ...settings, [key]: e.target.value })
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setSuccessMsg('')
    try {
      await updateSettings(settings)
      setSuccessMsg('System configuration updated successfully! Calculation engine is using new parameters.')
      await loadData()
    } catch (err) {
      alert(err.message || 'Failed to update settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Platform Settings & Calculation Parameters</h1>
          <p>Configure commercial tariffs, emission intensities, baseline thresholds, and equivalent factors.</p>
          <span className="sim-pill">{t('shell.simulated')}</span>
        </div>

        <div className="toolbar">
          <button type="button" className="btn btn--outline" onClick={loadData}>
            <RefreshCw size={16} /> Reset Form
          </button>
        </div>
      </header>

      {successMsg && (
        <div className="state-box" style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#065f46', marginBottom: 20 }}>
          <CheckCircle size={22} color="#059669" />
          <div>
            <strong>Parameters Saved</strong>
            <p>{successMsg}</p>
          </div>
        </div>
      )}

      {error && <ErrorState error={error} onRetry={loadData} />}

      {loading && !Object.keys(settings).length && (
        <div aria-busy="true">
          <Skeleton height={420} radius={14} />
        </div>
      )}

      {!loading && (
        <form onSubmit={handleSave}>
          <div className="grid-2" style={{ gap: 20 }}>
            {/* Electricity & Financial Parameters */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Electricity & Financial Model</h2>
                  <p className="card-sub">Commercial institutional utility tariffs and regional emission factors.</p>
                </div>
                <Sliders size={20} color="#1f8a5b" />
              </div>

              <div className="field">
                <label htmlFor="tariff">Commercial Tariff (₹ / kWh)</label>
                <input
                  id="tariff"
                  type="number"
                  step="0.05"
                  min="0.1"
                  value={settings.electricity_price_per_kwh || '8.50'}
                  onChange={handleChange('electricity_price_per_kwh')}
                  required
                />
                <span className="note-text">Representative Indian commercial educational institutional power tariff.</span>
              </div>

              <div className="field" style={{ marginTop: 14 }}>
                <label htmlFor="emissions">Grid Emission Factor (kg CO₂ / kWh)</label>
                <input
                  id="emissions"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={settings.emissions_factor_kg_per_kwh || '0.71'}
                  onChange={handleChange('emissions_factor_kg_per_kwh')}
                  required
                />
                <span className="note-text">Central Electricity Authority (CEA) average emission factor for regional grids.</span>
              </div>

              <div className="field" style={{ marginTop: 14 }}>
                <label htmlFor="fan">Ceiling Fan Equivalence (Watts)</label>
                <input
                  id="fan"
                  type="number"
                  step="1"
                  min="10"
                  value={settings.fan_watt_equivalent || '75.0'}
                  onChange={handleChange('fan_watt_equivalent')}
                  required
                />
                <span className="note-text">Wattage rating of standard campus ceiling fan used for human-readable equivalence.</span>
              </div>
            </section>

            {/* Water & Anomaly Thresholds */}
            <section className="card">
              <div className="card-head">
                <div>
                  <h2>Water Flow & Anomaly Detection</h2>
                  <p className="card-sub">Nocturnal flow parameters and conservation equivalence metrics.</p>
                </div>
                <SettingsIcon size={20} color="#0f8fa0" />
              </div>

              <div className="field">
                <label htmlFor="bucket">Utility Bucket Capacity (Litres)</label>
                <input
                  id="bucket"
                  type="number"
                  step="1"
                  min="1"
                  value={settings.bucket_litres || '15.0'}
                  onChange={handleChange('bucket_litres')}
                  required
                />
                <span className="note-text">Volume of a standard utility cleaning bucket used for water loss equivalence.</span>
              </div>

              <div className="field" style={{ marginTop: 14 }}>
                <label htmlFor="water-threshold">Nocturnal Leak Alert Threshold (L/h)</label>
                <input
                  id="water-threshold"
                  type="number"
                  step="1"
                  min="5"
                  value={settings.low_flow_threshold_lph || '50.0'}
                  onChange={handleChange('low_flow_threshold_lph')}
                  required
                />
                <span className="note-text">Flow exceeding this rate during inactive night hours (02:00–05:00) triggers alarms.</span>
              </div>

              <div className="field" style={{ marginTop: 14 }}>
                <label htmlFor="water-baseline">Expected Nocturnal Baseline Flow (L/h)</label>
                <input
                  id="water-baseline"
                  type="number"
                  step="1"
                  min="0"
                  value={settings.night_flow_baseline_lph || '15.0'}
                  onChange={handleChange('night_flow_baseline_lph')}
                  required
                />
                <span className="note-text">Normal background flow in risers from pilot valves and security washrooms.</span>
              </div>
            </section>
          </div>

          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <button type="submit" className="btn btn--primary" disabled={saving}>
              {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
              Save Configuration
            </button>
          </div>
        </form>
      )}
    </>
  )
}
