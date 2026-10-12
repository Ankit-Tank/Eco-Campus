// FAKE ANSWERS. Only used when VITE_USE_MOCK=true. The real assistant answers from backend data.
import { getMyComplaints } from './mockStudent.js'

const wait = (ms = 900) => new Promise((resolve) => setTimeout(resolve, ms))
const has = (text, words) => words.some((w) => text.includes(w))

export async function askAssistant(question) {
  await wait()
  const q = question.toLowerCase()

  if (has(q, ['status', 'my report', 'complaint', 'रिपोर्ट'])) {
    const { items } = await getMyComplaints()
    const open = items.filter((r) => ['submitted', 'accepted', 'in_progress'].includes(r.status)).length
    return { answer: `You have ${items.length} recent reports. ${open} of them are still open. You can see each one with its status in My Reports.`, is_simulated: true }
  }
  if (has(q, ['ghost'])) {
    return { answer: 'Ghost Load is electricity used beyond what a room is expected to need. For example, an AC left on in an empty room. It is a possible waste, not proof of waste, because some rooms have valid unscheduled use.', is_simulated: true }
  }
  if (has(q, ['leak', 'water', 'tap', 'पानी'])) {
    return { answer: 'To report a water problem, go to Home, fill in the Report a New Issue form with the place and a short description, and add a photo if you can. The administration will review it and you can follow its status in My Reports.', is_simulated: true }
  }
  if (has(q, ['save', 'electric', 'hostel', 'energy', 'बिजली'])) {
    return { answer: 'Switch off lights, fans and chargers when you leave the room, use the AC only when needed and at a moderate temperature, and report appliances left running in empty rooms. Small habits add up across a whole campus.', is_simulated: true }
  }
  return { answer: 'This is demo mode, so I can only answer a few sample questions. Try asking about Ghost Load, saving electricity, reporting a water leak, or the status of your reports.', is_simulated: true }
}
