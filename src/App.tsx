import { useEffect, useMemo, useRef, useState } from 'react'
import {
  BookOpen, CalendarDays, ChartNoAxesColumnIncreasing, Check, ChevronLeft, ChevronRight,
  Clock3, CloudRain, Coffee, Download, Headphones, Heart, KeyRound, ListTodo,
  MapPin, Music2, Pause, Play, Plus, RotateCcw, Send, Settings2, SlidersHorizontal,
  Sparkles, Sun, Trash2, Upload, Wind, X
} from 'lucide-react'
import { AmbientEngine, type AmbientKind } from './audio'
import { Companion, type Mood } from './Companion'
import {
  dayMinutes, initialSettings, initialTimer, localDate, phaseSeconds, timeLabel, uid, useSavedState,
  type ChatMessage, type FocusSession, type Phase, type Scene, type Settings, type Task, type Timer,
  type View, type Weather
} from './model'

const phaseName: Record<Phase, string> = { focus: '专注时间', short: '短暂休息', long: '长休息' }
const sceneName: Record<Scene, string> = { auto: '自动', day: '晴朗白昼', sunset: '日落黄昏', night: '安静夜晚', rain: '雨天小屋' }
const weekLabels = ['日','一','二','三','四','五','六']
const starter: ChatMessage[] = [{ id: 'welcome', role: 'assistant', content: '欢迎回到你的小窝喵。今天也一起慢慢来吧！' }]
const safeMinutes = (n: number) => Math.max(1, Math.min(180, Number.isFinite(n) ? Math.round(n) : 25))
const weatherDescription = (code: number) => code >= 95 ? '雷雨' : code >= 71 && code <= 77 ? '下雪' : code >= 51 && code <= 82 ? '下雨' : code <= 1 ? '晴朗' : code <= 3 ? '多云' : '阴天'
const isRain = (code: number) => (code >= 51 && code <= 82) || code >= 95

function ButtonIcon({ children, title, onClick, className = '' }: {children: React.ReactNode; title: string; onClick: () => void; className?: string}) {
  return <button className={'icon-button ' + className} title={title} aria-label={title} onClick={onClick}>{children}</button>
}

function useWeather(city: string) {
  const [weather, setWeather] = useState<Weather | null>(null)
  const [weatherError, setWeatherError] = useState(false)
  useEffect(() => {
    if (!city.trim()) return
    const controller = new AbortController()
    const update = async () => {
      try {
        const lookup = await fetch('https://geocoding-api.open-meteo.com/v1/search?name=' + encodeURIComponent(city.trim()) + '&count=1&language=zh&format=json', { signal: controller.signal })
        if (!lookup.ok) throw new Error('geocoding')
        const result = await lookup.json() as { results?: { latitude: number; longitude: number; name: string }[] }
        if (!result.results?.[0]) throw new Error('city')
        const place = result.results[0]
        const response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${place.latitude}&longitude=${place.longitude}&current=temperature_2m,weather_code,is_day&timezone=auto`, { signal: controller.signal })
        if (!response.ok) throw new Error('forecast')
        const data = await response.json() as { current?: { temperature_2m: number; weather_code: number; is_day: number } }
        if (!data.current) throw new Error('data')
        setWeather({ temperature: Math.round(data.current.temperature_2m), code: data.current.weather_code, isDay: data.current.is_day === 1, name: place.name })
        setWeatherError(false)
      } catch (error) {
        if (!controller.signal.aborted) setWeatherError(true)
      }
    }
    const kickoff = window.setTimeout(() => { void update() }, 550)
    const refresh = window.setInterval(() => { void update() }, 30 * 60 * 1000)
    return () => { controller.abort(); window.clearTimeout(kickoff); window.clearInterval(refresh) }
  }, [city])
  return { weather, weatherError }
}

function determineScene(choice: Scene, weather: Weather | null): Exclude<Scene, 'auto'> {
  if (choice !== 'auto') return choice
  if (weather && isRain(weather.code)) return 'rain'
  const hour = new Date().getHours()
  if (hour < 6 || hour >= 20) return 'night'
  if (hour >= 17) return 'sunset'
  return 'day'
}

function WeeklyChart({ sessions }: { sessions: FocusSession[] }) {
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setHours(12,0,0,0)
    d.setDate(d.getDate() - (6 - i))
    return { key: localDate(d), label: weekLabels[d.getDay()], minutes: dayMinutes(sessions, localDate(d)) }
  }), [sessions])
  const max = Math.max(60, ...days.map(d => d.minutes))
  return <div className="chart">
    {days.map(day => <div className="chart-col" key={day.key} title={day.minutes + ' 分钟'}>
      <div className="chart-bar-track"><div className={'chart-bar' + (day.key === localDate() ? ' today' : '')} style={{ height: (day.minutes / max * 100) + '%' }} /></div>
      <span>{day.label}</span>
    </div>)}
  </div>
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return <label className="setting-field"><span className="field-label">{label}</span>{children}{hint && <span className="field-hint">{hint}</span>}</label>
}

export default function App() {
  const [view, setView] = useState<View>('home')
  const [settings, setSettings] = useSavedState<Settings>('settings', initialSettings)
  const [tasks, setTasks] = useSavedState<Task[]>('tasks', [])
  const [sessions, setSessions] = useSavedState<FocusSession[]>('sessions', [])
  const [timer, setTimer] = useSavedState<Timer>('timer', initialTimer)
  const [chat, setChat] = useSavedState<ChatMessage[]>('chat', starter)
  const [now, setNow] = useState(Date.now())
  const [selectedDate, setSelectedDate] = useState(localDate())
  const [taskDraft, setTaskDraft] = useState('')
  const [draftPriority, setDraftPriority] = useState<Task['priority']>('normal')
  const [chatDraft, setChatDraft] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')
  const [key, setKey] = useState(() => sessionStorage.getItem('mewnook:apiKey') || '')
  const [ambientOn, setAmbientOn] = useState(false)
  const [ambientLevels, setAmbientLevels] = useState<Record<AmbientKind, number>>({ rain: 25, wind: 8, brown: 0 })
  const [tracks, setTracks] = useState<{name: string; url: string}[]>([])
  const [trackIndex, setTrackIndex] = useState(0)
  const [musicPlaying, setMusicPlaying] = useState(false)
  const [importError, setImportError] = useState('')
  const [moodOverride, setMoodOverride] = useState<Mood | null>(null)
  const [utilityPanel, setUtilityPanel] = useState<'timer' | 'music' | 'sound' | null>(null)
  const [chatExpanded, setChatExpanded] = useState(false)
  const [dialogueOffset, setDialogueOffset] = useState(0)
  const [showHud, setShowHud] = useState(true)
  const audio = useRef<AmbientEngine | null>(null)
  const musicRef = useRef<HTMLAudioElement | null>(null)
  const chatBottomRef = useRef<HTMLDivElement | null>(null)
  const endHandled = useRef<number | null>(null)
  const { weather, weatherError } = useWeather(settings.city)

  useEffect(() => {
    const handle = window.setInterval(() => setNow(Date.now()), 800)
    return () => window.clearInterval(handle)
  }, [])
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [chat.length, chatLoading])
  useEffect(() => () => { void audio.current?.stop() }, [])
  useEffect(() => () => { tracks.forEach(t => URL.revokeObjectURL(t.url)) }, [tracks])
  useEffect(() => {
    if (musicPlaying && tracks.length && musicRef.current?.paused) {
      void musicRef.current.play().catch(() => setMusicPlaying(false))
    }
  }, [trackIndex, musicPlaying, tracks.length])

  const remaining = timer.running && timer.endsAt ? Math.max(0, Math.ceil((timer.endsAt - now) / 1000)) : timer.remaining
  const currentDuration = phaseSeconds(timer.phase, settings)
  const progress = Math.min(100, Math.max(0, (1 - remaining / Math.max(1, currentDuration)) * 100))
  const todayMinutes = dayMinutes(sessions, localDate())
  const completedToday = tasks.filter(t => t.date === localDate() && t.done).length
  const todayTasks = tasks.filter(t => t.date === localDate())
  const plannedTasks = tasks.filter(t => t.date === selectedDate).sort((a,b) => Number(a.done)-Number(b.done) || Number(b.priority === 'high')-Number(a.priority === 'high'))
  const activeTask = tasks.find(t => t.id === timer.selectedTaskId)
  const roomScene = determineScene(settings.scene, weather)
  const nightArtReady = roomScene === 'night'
  const mood: Mood = moodOverride || (timer.phase === 'focus' && timer.running ? (activeTask ? 'typing' : 'reading') : timer.phase !== 'focus' ? 'stretch' : roomScene === 'night' ? 'sleepy' : 'idle')
  const showName = settings.nickname.trim() || '你'
  const panel = view !== 'home' ? view : utilityPanel
  const openPanel = (next: 'timer'|'music'|'sound'|'tasks'|'stats'|'settings') => {
    setChatExpanded(false)
    if (panel === next) { setView('home'); setUtilityPanel(null); return }
    if (next === 'tasks' || next === 'stats' || next === 'settings') {
      setView(next); setUtilityPanel(null)
    } else { setView('home'); setUtilityPanel(next) }
  }
  const closePanel = () => { setView('home'); setUtilityPanel(null) }
  const assistantLines = chat.filter(message => message.role === 'assistant')
  const latestDialogue = assistantLines[Math.max(0, assistantLines.length - 1 - dialogueOffset)]?.content || '今天也一起度过温柔的一天吧。'
  const greeting = now && new Date(now).getHours() >= 18 ? '晚上好' : new Date(now).getHours() < 11 ? '早上好' : '下午好'

  const saveSettings = (changes: Partial<Settings>) => setSettings(s => ({...s,...changes}))
  const selectPhase = (phase: Phase) => {
    endHandled.current = null
    setTimer(t => ({...t, phase, remaining: phaseSeconds(phase, settings), endsAt: null, running: false}))
  }
  const toggleTimer = () => {
    endHandled.current = null
    setTimer(t => t.running
      ? {...t, running: false, remaining: Math.max(0, Math.ceil(((t.endsAt || Date.now()) - Date.now()) / 1000)), endsAt: null}
      : {...t, running: true, endsAt: Date.now() + Math.max(1, t.remaining) * 1000})
  }
  const resetTimer = () => { endHandled.current = null; setTimer(t => ({ ...t, running: false, remaining: phaseSeconds(t.phase, settings), endsAt: null })) }
  useEffect(() => {
    if (!timer.running || !timer.endsAt || now < timer.endsAt || endHandled.current === timer.endsAt) return
    endHandled.current = timer.endsAt
    const isFocus = timer.phase === 'focus'
    if (isFocus) {
      const newSession: FocusSession = { id: uid(), taskId: timer.selectedTaskId, minutes: settings.focusMinutes, finishedAt: timer.endsAt }
      setSessions(s => [...s, newSession])
    }
    const focusCount = timer.focusCount + (isFocus ? 1 : 0)
    const nextPhase: Phase = isFocus ? (focusCount % Math.max(1,settings.longEvery) === 0 ? 'long' : 'short') : 'focus'
    const seconds = phaseSeconds(nextPhase, settings)
    setTimer(t => ({...t, phase: nextPhase, focusCount, remaining: seconds, running: settings.autoAdvance, endsAt: settings.autoAdvance ? Date.now() + seconds * 1000 : null}))
    setMoodOverride(isFocus ? 'happy' : null)
    if (settings.soundOnFinish) {
      try {
        const ctx = new AudioContext(), oscillator = ctx.createOscillator(), gain = ctx.createGain()
        oscillator.type = 'sine'; oscillator.frequency.value = 740; gain.gain.value = 0.035
        oscillator.connect(gain).connect(ctx.destination); oscillator.start(); oscillator.stop(ctx.currentTime + 0.16)
        oscillator.onended = () => { void ctx.close() }
      } catch { /* audio can be blocked by the browser */ }
    }
  }, [now, timer, settings, setSessions, setTimer])

  const addTask = () => {
    const title = taskDraft.trim()
    if (!title) return
    setTasks(old => [{ id: uid(), title, date: selectedDate, done: false, priority: draftPriority, createdAt: Date.now() }, ...old])
    setTaskDraft('')
  }
  const moveDay = (delta: number) => {
    const d = new Date(selectedDate + 'T12:00:00')
    d.setDate(d.getDate() + delta)
    setSelectedDate(localDate(d))
  }
  const updateTask = (id: string, changes: Partial<Task>) => setTasks(all => all.map(task => task.id === id ? {...task,...changes} : task))
  const updateDuration = (field: 'focusMinutes'|'shortMinutes'|'longMinutes', value: number) => {
    const minutes = safeMinutes(value)
    saveSettings({[field]: minutes})
    const phase = field === 'focusMinutes' ? 'focus' : field === 'shortMinutes' ? 'short' : 'long'
    if (!timer.running && timer.phase === phase) setTimer(t => ({...t, remaining: minutes * 60}))
  }

  async function toggleAmbient() {
    try {
      if (ambientOn) { await audio.current?.stop(); setAmbientOn(false); return }
      if (!audio.current) audio.current = new AmbientEngine()
      for (const kind of Object.keys(ambientLevels) as AmbientKind[]) audio.current.setVolume(kind, ambientLevels[kind] / 100)
      await audio.current.start()
      setAmbientOn(true)
    } catch { setAmbientOn(false) }
  }
  function levelChange(kind: AmbientKind, value: number) {
    setAmbientLevels(old => ({...old, [kind]: value}))
    audio.current?.setVolume(kind, value / 100)
  }
  function loadTracks(files: FileList | null) {
    if (!files) return
    const selected = Array.from(files).filter(f => f.type.startsWith('audio/') || /\.(mp3|m4a|wav|ogg|flac)$/i.test(f.name))
    setTracks(selected.map(file => ({ name: file.name, url: URL.createObjectURL(file) })))
    setTrackIndex(0)
    setMusicPlaying(false)
  }
  async function toggleMusic() {
    const element = musicRef.current
    if (!element || !tracks.length) return
    if (musicPlaying) { element.pause(); setMusicPlaying(false); return }
    try { await element.play(); setMusicPlaying(true) } catch { setMusicPlaying(false) }
  }
  const exportData = () => {
    const blob = new Blob([JSON.stringify({ version: 1, settings, tasks, sessions, chat }, null, 2)], {type:'application/json'})
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a'); link.href = url; link.download = 'mewnook-backup-' + localDate() + '.json'; link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 3000)
  }
  async function importData(file: File | undefined) {
    if (!file) return
    setImportError('')
    try {
      if (file.size > 5_000_000) throw new Error('备份文件不能超过 5MB')
      const data: unknown = JSON.parse(await file.text())
      if (!data || typeof data !== 'object' || !('version' in data) || data.version !== 1) throw new Error('不支持的备份文件')
      const backup = data as { settings?: Settings; tasks?: Task[]; sessions?: FocusSession[]; chat?: ChatMessage[] }
      if (!Array.isArray(backup.tasks) || !Array.isArray(backup.sessions) ||
        backup.tasks.some(t => !t || typeof t.title !== 'string' || typeof t.date !== 'string' || typeof t.id !== 'string') ||
        backup.sessions.some(s => !s || typeof s.minutes !== 'number' || typeof s.finishedAt !== 'number')) throw new Error('备份内容格式有误')
      setTasks(backup.tasks); setSessions(backup.sessions)
      if (backup.settings && typeof backup.settings === 'object') setSettings({...initialSettings,...backup.settings, aiUrl: typeof backup.settings.aiUrl === 'string' ? backup.settings.aiUrl : '', aiModel: typeof backup.settings.aiModel === 'string' ? backup.settings.aiModel : ''})
      if (Array.isArray(backup.chat)) setChat(backup.chat.filter(m => m && ['user','assistant'].includes(m.role) && typeof m.content === 'string').slice(-100))
    } catch (err) { setImportError(err instanceof Error ? err.message : '导入失败') }
  }

  async function sendChat() {
    const content = chatDraft.trim()
    if (!content || chatLoading) return
    const userMessage: ChatMessage = {id:uid(),role:'user',content}
    const history = [...chat, userMessage].slice(-20)
    setChat(previous => [...previous, userMessage].slice(-100))
    setChatDraft(''); setChatError(''); setDialogueOffset(0)
    setMoodOverride('chat')
    if (!settings.aiUrl.trim() || !settings.aiModel.trim()) {
      const answer = /累|困|休息/.test(content) ? '那就稍微休息一下吧。窗外的风也在等你呢。' :
        /学习|工作|专注|代码|任务/.test(content) ? '我们一起把这一小段时间认真过好喵。我会安静地陪着你。' :
        '喵呜～我在这里！想聊天的话随时可以找我。'
      setChat(previous => [...previous, {id:uid(),role:'assistant' as const,content:answer}].slice(-100))
      return
    }
    setChatLoading(true)
    try {
      const base = new URL(settings.aiUrl.trim())
      const isLoopback = ['localhost','127.0.0.1','[::1]','::1'].includes(base.hostname)
      if (base.protocol !== 'https:' && !(base.protocol === 'http:' && isLoopback)) throw new Error('请使用 HTTPS API 地址，本地服务可使用 localhost')
      if (base.username || base.password || base.search || base.hash) throw new Error('API URL 请勿包含账号信息或查询参数')
      const endpoint = base.pathname.replace(/\/+$/,'').endsWith('/chat/completions') ? base.toString() :
        base.toString().replace(/\/+$/,'') + '/chat/completions'
      const reply = await fetch(endpoint, {
        method:'POST', headers: {'Content-Type':'application/json', ...(key ? {Authorization:'Bearer ' + key} : {})},
        body: JSON.stringify({model:settings.aiModel,stream:false,temperature:0.8,
          messages:[{role:'system',content:`你是一位白发蓝瞳、性格温柔俏皮的猫娘，是用户在 MewNook 的专注伙伴。用自然简短的中文回复，不要过度打扰。当前状态：${phaseName[timer.phase]}。正在做：${activeTask?.title || '自由安排'}。你不能直接操作用户的任务。`},
            ...history.map(m => ({role:m.role,content:m.content}))]})
      })
      if (!reply.ok) throw new Error('API 返回 HTTP ' + reply.status + '，请检查地址、模型、Key 或额度')
      const data = await reply.json() as { choices?: {message?: {content?: string}}[] }
      const answer = data.choices?.[0]?.message?.content?.trim()
      if (!answer) throw new Error('API 未返回可显示的回复')
      setChat(previous => [...previous,{id:uid(),role:'assistant' as const,content:answer}].slice(-100))
    } catch (error) {
      setChatError(error instanceof TypeError ? '网络请求失败。请检查网络、API 地址和服务商是否允许浏览器跨域（CORS）。' : error instanceof Error ? error.message : '请求失败')
    } finally { setChatLoading(false) }
  }

  return <div className={'immersive-shell accent-' + settings.accent + ' backdrop-' + roomScene}>
    <div className={'room-stage' + (nightArtReady ? ' has-night-art' : '')} aria-label="沉浸式猫娘工作空间">
      {nightArtReady && <div className="art-stage">
        <img className="art-background" src="/assets/rooms/night/background.webp" alt="" draggable={false}/>
        <button className="art-character" aria-label="摸摸猫娘的头" onClick={() => setMoodOverride(m => m === 'happy' ? null : 'happy')}>
          <img src="/assets/rooms/night/character.webp" alt="夜间在书桌旁打哈欠的白发蓝瞳猫娘" draggable={false}/>
        </button>
        <img className="art-foreground" src="/assets/rooms/night/foreground.webp" alt="" draggable={false}/>
      </div>}
      <div className="room-wall-texture" aria-hidden="true"/>
      <div className="room-window" aria-hidden="true"><div className="window-moon"/><div className="window-hills"/><div className="window-city"/><div className="window-rain"/><div className="window-frame cross"/><div className="window-frame vertical"/></div>
      <div className="room-curtain curtain-left" aria-hidden="true"/><div className="room-curtain curtain-right" aria-hidden="true"/>
      <div className="room-light" aria-hidden="true"/><div className="room-stringlights" aria-hidden="true"><i/><i/><i/><i/><i/><i/></div>
      <div className="room-wall-pictures" aria-hidden="true"><i/><i/></div>
      <div className="room-floating-shelf" aria-hidden="true"><span className="room-books">▰ ▥ ▥ ▰</span><span className="room-vase">✿</span></div>
      <div className="room-plant" aria-hidden="true"><span>❦</span></div>
      <div className="room-rug" aria-hidden="true"/>
      <div className="room-desk" aria-hidden="true"><span className="desk-monitor"/><span className="desk-cup"/><span className="desk-book"/></div>
      <div className="room-dust" aria-hidden="true"><span/><span/><span/><span/><span/><span/></div>
      <button type="button" className="character-actor" onClick={() => setMoodOverride(m => m === 'happy' ? null : 'happy')} aria-label="摸摸猫娘的头">
        <Companion mood={mood} phase={timer.phase}/>
      </button>
    </div>

    <header className="scene-topbar">
      <div className="scene-brand"><span className="brand-paw">✿</span><span><b>MewNook</b><small>YOUR COZY CORNER</small></span></div>
      {showHud && <div className="scene-status"><span><Clock3 size={14}/> {new Intl.DateTimeFormat('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(now))}</span><span className="status-separator">✧</span><span><MapPin size={13}/> {weather?.name || settings.city}</span><span className="status-separator">✧</span><span>{weather ? weather.temperature + '° · ' + weatherDescription(weather.code) : weatherError ? '天气暂不可用' : '天气加载中'}</span></div>}
      <button className="topbar-toggle" onClick={() => setShowHud(v => !v)} aria-label={showHud ? '隐藏顶部信息' : '显示顶部信息'} title="隐藏或显示顶部信息">{showHud ? <SlidersHorizontal size={17}/> : <Sun size={17}/>}</button>
    </header>

    <nav className="float-dock float-dock-left" aria-label="工作工具">
      <button className={'dock-button' + (panel === 'timer' ? ' selected' : '')} onClick={() => openPanel('timer')} title="番茄钟" aria-label="番茄钟"><Clock3 size={21}/><span>专注</span></button>
      <button className={'dock-button' + (panel === 'tasks' ? ' selected' : '')} onClick={() => openPanel('tasks')} title="任务日程" aria-label="任务日程"><ListTodo size={21}/><span>日程</span></button>
      <button className={'dock-button' + (panel === 'stats' ? ' selected' : '')} onClick={() => openPanel('stats')} title="专注统计" aria-label="专注统计"><ChartNoAxesColumnIncreasing size={21}/><span>统计</span></button>
      <span className="dock-divider" aria-hidden="true"/>
      <button className={'dock-button' + (panel === 'settings' ? ' selected' : '')} onClick={() => openPanel('settings')} title="设置" aria-label="设置"><Settings2 size={21}/><span>设置</span></button>
    </nav>
    <nav className="float-dock float-dock-right" aria-label="环境与互动">
      <button className={'dock-button' + (panel === 'music' ? ' selected' : '')} onClick={() => openPanel('music')} title="我的音乐" aria-label="我的音乐"><Music2 size={21}/><span>音乐</span></button>
      <button className={'dock-button' + (panel === 'sound' ? ' selected' : '')} onClick={() => openPanel('sound')} title="环境音" aria-label="环境音"><Headphones size={21}/><span>环境</span></button>
      <button className={'dock-button' + (chatExpanded ? ' selected' : '')} onClick={() => {setChatExpanded(v => !v);closePanel()}} title="与猫娘聊天" aria-label="与猫娘聊天"><Heart size={21}/><span>聊天</span></button>
    </nav>

    {showHud && <div className="scene-focus-chip">
      <span className={'focus-dot' + (timer.running ? ' active' : '')}/>
      <span>{timer.running ? '一起努力中' : phaseName[timer.phase]}</span>
      <b>{timeLabel(remaining)}</b>
      <button onClick={toggleTimer} aria-label={timer.running ? '暂停计时' : '开始或继续计时'} title={timer.running ? '暂停' : '开始'}>{timer.running ? <Pause size={15}/> : <Play size={15} fill="currentColor"/>}</button>
      <button onClick={() => openPanel('timer')} aria-label="打开番茄钟设置" title="更多计时选项"><ChevronRight size={15}/></button>
    </div>}

    <div className="scene-corner-line">✦ {greeting}，{showName}。 <span>今天也一起慢慢来。</span></div>

    {panel && <>
      <button type="button" className="overlay-scrim" aria-label="关闭功能面板" onClick={closePanel}/>
      <aside className={'immersive-drawer' + (panel === 'music' || panel === 'sound' ? ' right-drawer' : '')} aria-label={panel === 'timer' ? '番茄钟' : panel === 'tasks' ? '日程' : panel === 'stats' ? '统计' : panel === 'settings' ? '设置' : panel === 'music' ? '音乐' : '环境音'}>
        <div className="drawer-top">
          <div><small>MEWNOOK · LITTLE MOMENTS</small><h2>{panel === 'timer' ? '一起专注' : panel === 'tasks' ? '日程与任务' : panel === 'stats' ? '专注统计' : panel === 'settings' ? '偏好设置' : panel === 'music' ? '我的音乐' : '声音空间'}</h2></div>
          <button className="drawer-close" onClick={closePanel} aria-label="关闭面板"><X size={20}/></button>
        </div>
        <div className="drawer-scroll">
        {panel === 'timer' && <section className="panel timer-panel">
          <div className="panel-heading"><div><span className="section-icon lilac"><Clock3 size={18}/></span><strong>番茄钟</strong></div><span className="muted-small">FOCUS WITH ME</span></div>
          <div className="phase-switch">
            {(['focus','short','long'] as Phase[]).map(phase => <button key={phase} className={timer.phase === phase ? 'selected' : ''} onClick={() => selectPhase(phase)}>{phaseName[phase]}</button>)}
          </div>
          <div className="clock-display"><span>{timeLabel(remaining)}</span><svg viewBox="0 0 270 12" preserveAspectRatio="none"><rect width="270" height="12" rx="6" fill="#e8e7f1"/><rect width={270 * progress / 100} height="12" rx="6" fill="#8b98ce"/></svg></div>
          <div className="timer-actions"><button className="primary-button" onClick={toggleTimer}>{timer.running ? <Pause size={18}/> : <Play size={18} fill="currentColor"/>}{timer.running ? '暂停专注' : remaining < currentDuration ? '继续计时' : '开始专注'}</button><ButtonIcon title="重置当前计时" onClick={resetTimer}><RotateCcw size={18}/></ButtonIcon></div>
          <div className="timer-task"><span>本轮任务</span><select aria-label="本轮专注关联任务" value={timer.selectedTaskId || ''} onChange={e => setTimer(t => ({...t,selectedTaskId:e.target.value || null}))}><option value="">自由专注</option>{tasks.filter(t=>!t.done).map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></div>
          <div className="timer-summary"><span><Sparkles size={16}/> 今日累计 <strong>{todayMinutes} 分钟</strong></span><span><Check size={16}/> 完成 <strong>{completedToday}/{todayTasks.length} 项</strong></span></div>
          <button className="drawer-secondary-link" onClick={() => openPanel('tasks')}>安排今天的计划 <ChevronRight size={16}/></button>
        </section>}
        {view === 'tasks' && <section className="panel full-panel">
          <div className="panel-heading large"><div><span className="section-icon peach"><CalendarDays size={20}/></span><strong>每日计划</strong></div><button className="light-button" onClick={()=>setSelectedDate(localDate())}>回到今天</button></div>
          <div className="calendar-header"><ButtonIcon title="前一天" onClick={()=>moveDay(-1)}><ChevronLeft size={20}/></ButtonIcon><h3>{new Intl.DateTimeFormat('zh-CN',{year:'numeric',month:'long',day:'numeric',weekday:'long'}).format(new Date(selectedDate + 'T12:00:00'))}</h3><ButtonIcon title="后一天" onClick={()=>moveDay(1)}><ChevronRight size={20}/></ButtonIcon></div>
          <div className="week-strip">{Array.from({length:7},(_,i)=>{const d = new Date(selectedDate+'T12:00:00');d.setDate(d.getDate()+i-3);const date=localDate(d);return <button key={date} className={selectedDate===date?'active':''} onClick={()=>setSelectedDate(date)}><span>周{weekLabels[d.getDay()]}</span><b>{d.getDate()}</b></button>})}</div>
          <div className="task-entry"><input value={taskDraft} onChange={e=>setTaskDraft(e.target.value)} onKeyDown={e=>e.key==='Enter'&&addTask()} placeholder="写下一件想完成的事…" maxLength={140}/><button className="light-button" onClick={()=>setDraftPriority(p=>p==='high'?'normal':'high')} title="切换优先级">{draftPriority==='high'?'⭐ 重要':'普通'}</button><button className="primary-button" onClick={addTask}><Plus size={17}/> 添加</button></div>
          <div className="task-section-title">计划列表 <span>{plannedTasks.filter(t=>t.done).length}/{plannedTasks.length} 已完成</span></div>
          {plannedTasks.length === 0 && <div className="empty-state"><BookOpen size={34}/><h3>还没有任务安排</h3><p>从一件小事开始，也是在向前走喵。</p></div>}
          <div className="task-list">{plannedTasks.map(t=><div className={'task-row' + (t.done?' completed':'')} key={t.id}><label><input type="checkbox" checked={t.done} onChange={e=>updateTask(t.id,{done:e.target.checked})}/><span>{t.title}</span></label>{t.priority==='high'&&<span className="high-priority">重要</span>}<button className="light-button small" onClick={()=>{setTimer(s=>({...s,selectedTaskId:t.id}));setView('home')}}>专注</button><ButtonIcon title="删除任务" onClick={()=>{setTasks(all=>all.filter(item=>item.id!==t.id));if(timer.selectedTaskId===t.id)setTimer(old=>({...old,selectedTaskId:null}))}}><Trash2 size={17}/></ButtonIcon></div>)}</div>
        </section>}
        {view === 'stats' && <div className="stats-view">
          <div className="stats-summary"><div className="stat-tile"><span><Clock3 size={17}/> 累计专注</span><strong>{sessions.reduce((a,s)=>a+s.minutes,0)} <small>分钟</small></strong></div><div className="stat-tile"><span><Sparkles size={17}/> 完成番茄钟</span><strong>{sessions.length} <small>次</small></strong></div><div className="stat-tile"><span><Check size={17}/> 已完成任务</span><strong>{tasks.filter(t=>t.done).length} <small>项</small></strong></div></div>
          <section className="panel full-panel"><div className="panel-heading"><div><span className="section-icon blue"><ChartNoAxesColumnIncreasing size={18}/></span><strong>近七天专注时长</strong></div><span className="muted-small">单位：分钟</span></div><WeeklyChart sessions={sessions}/></section>
          <section className="panel full-panel"><div className="panel-heading"><div><span className="section-icon lilac"><BookOpen size={18}/></span><strong>最近的专注记录</strong></div></div>{sessions.length===0?<div className="empty-state"><Clock3 size={32}/><h3>尚无专注记录</h3><p>完成第一个专注时段，这里就会开始记录。</p></div>:<div className="session-list">{[...sessions].reverse().slice(0,15).map(s=><div key={s.id}><span>{new Intl.DateTimeFormat('zh-CN',{dateStyle:'medium',timeStyle:'short'}).format(new Date(s.finishedAt))}</span><span>{tasks.find(t=>t.id===s.taskId)?.title||'自由专注'}</span><b>{s.minutes} 分钟</b></div>)}</div>}</section>
        </div>}
        {view === 'settings' && <div className="settings-view">
          <section className="panel full-panel"><div className="panel-heading large"><div><span className="section-icon lilac"><SlidersHorizontal size={20}/></span><strong>番茄钟偏好</strong></div></div>
            <div className="settings-grid">{(['focusMinutes','shortMinutes','longMinutes'] as const).map((field,i)=><Field key={field} label={['专注时长（分钟）','短休息（分钟）','长休息（分钟）'][i]}><input type="number" min="1" max="180" value={settings[field]} onChange={e=>updateDuration(field,Number(e.target.value))}/></Field>)}
              <Field label="每几轮长休息"><input type="number" min="1" max="12" value={settings.longEvery} onChange={e=>saveSettings({longEvery:Math.max(1,Math.min(12,Number(e.target.value)||4))})}/></Field></div>
            <div className="switch-row"><div><b>自动开始下一轮</b><span>一轮结束后自动运行下个计时</span></div><input type="checkbox" checked={settings.autoAdvance} onChange={e=>saveSettings({autoAdvance:e.target.checked})}/></div>
            <div className="switch-row"><div><b>计时完成提示音</b><span>浏览器可能限制后台自动播放</span></div><input type="checkbox" checked={settings.soundOnFinish} onChange={e=>saveSettings({soundOnFinish:e.target.checked})}/></div>
          </section>
          <section className="panel full-panel"><div className="panel-heading large"><div><span className="section-icon peach"><Sun size={20}/></span><strong>虚拟房间</strong></div></div><div className="settings-grid">
            <Field label="称呼"><input value={settings.nickname} maxLength={24} onChange={e=>saveSettings({nickname:e.target.value})}/></Field>
            <Field label="天气城市" hint="使用 Open-Meteo，城市名支持中文或英文。"><input value={settings.city} onChange={e=>saveSettings({city:e.target.value})}/></Field>
            <Field label="场景"><select value={settings.scene} onChange={e=>saveSettings({scene:e.target.value as Scene})}>{(Object.keys(sceneName) as Scene[]).map(scene=><option key={scene} value={scene}>{sceneName[scene]}</option>)}</select></Field>
            <Field label="主题配色"><select value={settings.accent} onChange={e=>saveSettings({accent:e.target.value as Settings['accent']})}><option value="blue">雾蓝</option><option value="pink">樱粉</option><option value="lavender">淡紫</option></select></Field>
          </div><p className="footnote">天气数据：<a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a> · 非商业使用请遵守其许可与署名要求。</p></section>
          <section className="panel full-panel"><div className="panel-heading large"><div><span className="section-icon blue"><KeyRound size={20}/></span><strong>自定义 AI API</strong></div><span className="badge">BYOK · 可选</span></div>
            <p className="settings-intro">没有 API 也能使用预设猫娘对话。使用第三方模型时，由浏览器直接向你的服务商发起请求，必须支持 CORS。项目不提供付费 Key，也没有云端中转。</p>
            <div className="settings-grid"><Field label="OpenAI 兼容 API Base URL" hint="例如 https://api.example.com/v1"><input autoComplete="off" type="url" placeholder="https://api.example.com/v1" value={settings.aiUrl} onChange={e=>saveSettings({aiUrl:e.target.value})}/></Field>
              <Field label="模型 ID"><input placeholder="model-name" value={settings.aiModel} onChange={e=>saveSettings({aiModel:e.target.value})}/></Field>
              <Field label="API Key" hint="仅保存在当前浏览器会话的 sessionStorage，关闭标签页后通常会清除。"><input type="password" autoComplete="off" placeholder="sk-..." value={key} onChange={e=>{setKey(e.target.value);sessionStorage.setItem('mewnook:apiKey',e.target.value)}}/></Field></div>
            <p className="footnote">⚠ Key 会发送给你填写的服务商。只使用可信 API 地址；前端会话存储不能防御恶意浏览器扩展或 XSS。</p>
          </section>
          <section className="panel full-panel"><div className="panel-heading large"><div><span className="section-icon peach"><Download size={20}/></span><strong>本地数据</strong></div></div><p className="settings-intro">数据只保存在当前浏览器，清理网站数据会删除记录。建议定期备份，不包含 API Key 或本地音乐文件。</p>
            <div className="data-actions"><button className="light-button" onClick={exportData}><Download size={17}/> 导出 JSON 备份</button><label className="light-button file-label"><Upload size={17}/> 导入 JSON 备份<input type="file" accept="application/json,.json" hidden onChange={e=>{void importData(e.target.files?.[0]);e.target.value=''}}/></label></div>{importError&&<p className="error-text">{importError}</p>}</section>
        </div>}
        {panel === 'sound' && <section className="panel">
          <div className="drawer-intro">让雨声与微风陪伴你，不需要下载任何背景音资源。</div>
          <div className="ambience-list">
            {([
              {kind:'rain' as AmbientKind,name:'轻轻雨声',icon:<CloudRain size={20}/>},
              {kind:'wind' as AmbientKind,name:'窗边微风',icon:<Wind size={20}/>},
              {kind:'brown' as AmbientKind,name:'柔和底噪',icon:<Coffee size={20}/>}
            ]).map(item => <div className="ambience-row" key={item.kind}><span className="ambience-icon">{item.icon}</span><span>{item.name}</span><input aria-label={item.name+'音量'} type="range" min="0" max="100" value={ambientLevels[item.kind]} onChange={e=>levelChange(item.kind,Number(e.target.value))}/><small>{ambientLevels[item.kind]}%</small></div>)}
          </div>
          <button className="primary-button wide-button" onClick={() => void toggleAmbient()}>{ambientOn ? <Pause size={18}/> : <Play size={18}/>} {ambientOn ? '暂停环境音' : '播放环境音'}</button>
          <div className="drawer-subheading">窗外风景</div><div className="scene-selector">{(Object.keys(sceneName) as Scene[]).map(scene => <button className={settings.scene===scene?'active':''} key={scene} onClick={()=>saveSettings({scene})}>{sceneName[scene]}</button>)}</div>
        </section>}
        {panel === 'music' && <section className="panel">
          <div className="drawer-intro">本地音乐只在你的设备上播放，不上传服务器。</div>
          <label className="music-import"><Plus size={18}/> 选择本地音乐<input type="file" accept="audio/*,.flac" multiple hidden onChange={e=>loadTracks(e.target.files)}/></label>
          {tracks.length > 0 ? <div className="music-player"><div className="track-name">♫ {tracks[trackIndex]?.name}</div><button className="primary-button wide-button" onClick={() => void toggleMusic()}>{musicPlaying ? <Pause size={17}/> : <Play size={17}/>} {musicPlaying ? '暂停音乐' : '播放音乐'}</button><div className="track-nav"><button onClick={()=>setTrackIndex(i=>(i+tracks.length-1)%tracks.length)}><ChevronLeft size={16}/> 上一首</button><span>{trackIndex+1}/{tracks.length}</span><button onClick={()=>setTrackIndex(i=>(i+1)%tracks.length)}>下一首 <ChevronRight size={16}/></button></div></div> : <div className="music-empty">这里还没有音乐。选择本地音频文件后就能开始播放；刷新页面后需要重新选择。</div>}
        </section>}
        </div>
      </aside>
    </>}

    <section className={'vn-dialogue' + (chatExpanded ? ' expanded' : '')} aria-label="和猫娘对话">
      <div className="vn-frame-ornament" aria-hidden="true">✧</div>
      <div className="vn-nameplate"><span>✦</span> 小猫同学 <span className="vn-name-en">COMPANION</span></div>
      {!chatExpanded ? <>
        <p className="vn-line" aria-live="polite">{timer.running && dialogueOffset === 0 && chat.length <= 1 ? '嘘…专注的时候，我也会安静地陪着你。' : latestDialogue}</p>
        <div className="vn-bottom">
          <span className="vn-hint">{settings.aiUrl && settings.aiModel ? 'AI 陪伴模式' : '离线预设台词'} · 点击「聊天」展开自由对话</span>
          <div className="vn-actions">
            <button disabled={dialogueOffset >= assistantLines.length - 1} onClick={()=>setDialogueOffset(i=>Math.min(assistantLines.length-1,i+1))} title="上一句台词" aria-label="上一句台词"><ChevronLeft size={17}/></button>
            <button disabled={dialogueOffset===0} onClick={()=>setDialogueOffset(i=>Math.max(0,i-1))} title="下一句台词" aria-label="下一句台词"><ChevronRight size={17}/></button>
            <button className="vn-chat-button" onClick={()=>setChatExpanded(true)} aria-label="展开聊天"><Send size={16}/> 聊天</button>
          </div>
        </div>
      </> : <>
        <div className="vn-history" aria-live="polite">{chat.map(message=><div key={message.id} className={'vn-message '+message.role}><span>{message.role==='assistant'?'小猫同学':'你'}</span><p>{message.content}</p></div>)}{chatLoading&&<p className="vn-typing">小猫正在想怎么回复你…</p>}{chatError&&<p className="chat-error">{chatError}</p>}<div ref={chatBottomRef}/></div>
        <form className="vn-compose" onSubmit={e=>{e.preventDefault();void sendChat()}}>
          <input aria-label="和猫娘说话" placeholder="和小猫说点什么…" maxLength={1600} value={chatDraft} onChange={e=>setChatDraft(e.target.value)} />
          <button disabled={chatLoading||!chatDraft.trim()} type="submit" aria-label="发送消息"><Send size={19}/></button>
          <button type="button" className="vn-collapse" onClick={()=>setChatExpanded(false)} aria-label="收起聊天"><X size={18}/></button>
        </form>
      </>}
    </section>
    <audio className="persistent-music" ref={musicRef} preload="metadata" src={tracks[trackIndex]?.url} onEnded={()=>setTrackIndex(i=>(i+1)%tracks.length)} />
    <div className="scene-attribution"><span>Weather · Open-Meteo</span>　✧　MewNook</div>
  </div>
}
