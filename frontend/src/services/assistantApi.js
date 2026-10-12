// Wraps backend/app/routes/assistant.py   (URL starts with /api/assistant)
import { post } from './httpClient.js'
import { USE_MOCK } from '../config.js'
import * as mock from './mock/mockAssistant.js'

// POST /api/assistant/ask   { question }
//   -> { answer, is_simulated }
// The backend must ground numbers in its own data and only use what the logged-in user may see.
// It should reply in the language of the Accept-Language header (sent automatically by httpClient).
export async function askAssistant(question) {
  if (USE_MOCK) return mock.askAssistant(question)
  const res = await post('/assistant/ask', { question })
  return {
    ...res,
    is_simulated: Boolean(res?.is_simulated || res?.data_source === 'simulated'),
  }
}
