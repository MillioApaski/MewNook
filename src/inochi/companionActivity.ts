export type CompanionActivity = 'focus' | 'rest' | 'idle' | 'chat' | 'sleepy'

/** Visual text delivery only; this is not audio lip-sync. */
export function speechDuration(text: string): number {
  if (!text.trim()) return 0
  return Math.min(6500, Math.max(1200, Array.from(text.trim()).length * 110))
}

export function companionActivity(input: {
  phase: string
  running: boolean
  night: boolean
  speaking: boolean
}): CompanionActivity {
  if (input.speaking) return 'chat'
  if (input.phase === 'focus' && input.running) return 'focus'
  if (input.phase !== 'focus') return 'rest'
  return input.night ? 'sleepy' : 'idle'
}
