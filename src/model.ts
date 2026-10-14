import { useEffect, useState } from 'react'
import { DEFAULT_COMPANION_PROMPT } from './companionPersona'

export type Phase = 'focus' | 'short' | 'long'
export type View = 'home' | 'tasks' | 'stats' | 'settings'
export type Scene = 'auto' | 'day' | 'sunset' | 'night' | 'rain'
export type Task = { id: string; title: string; date: string; done: boolean; priority: 'normal' | 'high'; createdAt: number }
export type FocusSession = { id: string; taskId: string | null; finishedAt: number; minutes: number }
export type Timer = { phase: Phase; running: boolean; endsAt: number | null; remaining: number; focusCount: number; selectedTaskId: string | null }
export type Settings = {
  focusMinutes: number; shortMinutes: number; longMinutes: number; longEvery: number;
  autoAdvance: boolean; soundOnFinish: boolean; city: string; scene: Scene;
  aiUrl: string; aiModel: string; aiPersonaPrompt: string; nickname: string; accent: 'blue' | 'pink' | 'lavender';
  aiStreaming: boolean; aiContextTurns: number; aiMaxTokens: number; aiMemory: string;
  proactiveEnabled: boolean; proactiveAI: boolean; proactiveIntervalMinutes: number; proactiveDailyLimit: number;
  inochiTestMode: boolean; inochiScale: number
}
export type ChatMessage = { id: string; role: 'user' | 'assistant'; content: string }
export type Weather = { temperature: number; code: number; isDay: boolean; name: string }

export const initialSettings: Settings = {
  focusMinutes: 25, shortMinutes: 5, longMinutes: 15, longEvery: 4,
  autoAdvance: false, soundOnFinish: true, city: 'Tokyo', scene: 'auto',
  aiUrl: '', aiModel: '', aiPersonaPrompt: DEFAULT_COMPANION_PROMPT, nickname: '你', accent: 'blue',
  aiStreaming: true, aiContextTurns: 12, aiMaxTokens: 600, aiMemory: '',
  proactiveEnabled: false, proactiveAI: false, proactiveIntervalMinutes: 60, proactiveDailyLimit: 2,
  inochiTestMode: false, inochiScale: 0.32
}
export const initialTimer: Timer = { phase: 'focus', running: false, endsAt: null, remaining: 25 * 60, focusCount: 0, selectedTaskId: null }
export const uid = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto) ? crypto.randomUUID() : Math.random().toString(36).slice(2)
export const localDate = (d = new Date()) => [d.getFullYear(), String(d.getMonth() + 1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-')
export const timeLabel = (seconds: number) => {
  const safe = Math.max(0, Math.ceil(seconds))
  return `${String(Math.floor(safe / 60)).padStart(2, '0')}:${String(safe % 60).padStart(2, '0')}`
}
export const phaseSeconds = (phase: Phase, settings: Settings) => ({
  focus: settings.focusMinutes, short: settings.shortMinutes, long: settings.longMinutes
}[phase] * 60)
export const dayMinutes = (sessions: FocusSession[], date: string) =>
  sessions.filter(s => localDate(new Date(s.finishedAt)) === date).reduce((sum,s) => sum + s.minutes, 0)

export function useSavedState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const saved = localStorage.getItem('mewnook:' + key)
      if (!saved) return initial
      const parsed: unknown = JSON.parse(saved)
      if (Array.isArray(initial)) return (Array.isArray(parsed) ? parsed : initial) as T
      if (initial && typeof initial === 'object' && parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return { ...initial, ...parsed } as T
      return (parsed as T) ?? initial
    } catch { return initial }
  })
  useEffect(() => {
    try { localStorage.setItem('mewnook:' + key, JSON.stringify(value)) }
    catch { /* storage full or blocked; app remains usable */ }
  }, [key, value])
  return [value, setValue] as const
}
