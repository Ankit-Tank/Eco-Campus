// Wraps backend/app/routes/rooms.py (URL /api/rooms)
import { post, request } from './httpClient.js'

export function getRooms({ block } = {}) {
  const params = new URLSearchParams()
  if (block && block !== 'all') params.append('block', block)
  return request(`/rooms?${params.toString()}`)
}

export function getRoom(id) {
  return request(`/rooms/${id}`)
}

export function getRoomEquipment(roomId) {
  return request(`/rooms/${roomId}/equipment`)
}

// ---- admin only (the backend enforces the role) ----
export function createRoom({ room_code, block, name, room_type, capacity, idle_baseline_kw }) {
  return post('/rooms', { room_code, block, name, room_type, capacity: Number(capacity), idle_baseline_kw: Number(idle_baseline_kw) })
}

export function updateRoom(id, fields) {
  return request(`/rooms/${id}`, { method: 'PUT', body: JSON.stringify(fields) })
}

export function deleteRoom(id) {
  return request(`/rooms/${id}`, { method: 'DELETE' })
}

export function createEquipment(roomId, { kind, rated_kw, count, expected_in_class, state = 'OFF' }) {
  return post(`/rooms/${roomId}/equipment`, {
    kind,
    rated_kw: Number(rated_kw),
    count: Number(count),
    expected_in_class: Number(expected_in_class),
    state,
  })
}

export function updateEquipment(equipmentId, fields) {
  return request(`/rooms/equipment/${equipmentId}`, { method: 'PUT', body: JSON.stringify(fields) })
}

export function deleteEquipment(equipmentId) {
  return request(`/rooms/equipment/${equipmentId}`, { method: 'DELETE' })
}
