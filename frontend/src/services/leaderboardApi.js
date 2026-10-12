// Wraps backend/app/routes/leaderboard.py (URL /api/leaderboard)
import { request } from './httpClient.js'

export function getBlockLeaderboard(period = '7d') {
  return request(`/leaderboard/blocks?period=${period}`)
}
