// Wraps backend/app/routes/simulator.py and live.py
import { post, request } from './httpClient.js'

export function getSimState() {
  return request('/sim/state')
}

export function startSim() {
  return post('/sim/start', {})
}

export function pauseSim() {
  return post('/sim/pause', {})
}

export function setSimSpeed(speed) {
  return post('/sim/speed', { speed: Number(speed) })
}

export function resetSim(timestamp) {
  return post('/sim/reset', timestamp ? { timestamp } : {})
}

export function triggerDemoScenario() {
  return post('/sim/scenario/demo', {})
}

export function setApplianceState({ equipment_id, state }) {
  return post('/sim/appliance', { equipment_id: Number(equipment_id), state })
}

export function tickSim(delta_minutes = 15) {
  return post('/sim/tick', { delta_minutes })
}

export function getLiveSnapshot() {
  return request('/live/snapshot')
}
