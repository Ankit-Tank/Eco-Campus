// Wraps backend/app/routes/rooms.py (URL /api/rooms)
import { request } from './httpClient.js'

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
