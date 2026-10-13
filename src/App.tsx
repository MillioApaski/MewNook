import { useEffect, useMemo, useRef, useState } from 'react'
import {
  BookOpen, CalendarDays, ChartNoAxesColumnIncreasing, Check, ChevronLeft, ChevronRight,
  Clock3, CloudRain, Coffee, Download, Headphones, Heart, Home, KeyRound, ListTodo,
  MapPin, MoonStar, Music2, Pause, Play, Plus, RotateCcw, Send, Settings2, SlidersHorizontal,
  Sparkles, Sun, Trash2, Upload, Volume2, VolumeX, Wind, X
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

const NavButton = ({active,icon,label,onClick}: {active: boolean;icon: React.ReactNode; label: string;onClick:()=>void}) =>
  <button className={'nav-item' + (active ? ' active' : '')} onClick={onClick}>{icon}<span>{label}</span>{active && <span className="nav-dot" />}</button>

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
  const [importError, setImportError] = useState('')
  const [mobileNav, setMobileNav] = useState(false)
  const [moodOverride, setMoodOverride] = useState<Mood | null>(null)
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

  const remaining = timer.running && timer.endsAt ? Math.max(0, Math.ceil((timer.endsAt - now) / 1000)) : timer.remaining
  const currentDuration = phaseSeconds(timer.phase, settings)
  const progress = Math.min(100, Math.max(0, (1 - remaining / Math.max(1, currentDuration)) * 100))
  const todayMinutes = dayMinutes(sessions, localDate())
  const completedToday = tasks.filter(t => t.date === localDate() && t.done).length
  const todayTasks = tasks.filter(t => t.date === localDate())
  const plannedTasks = tasks.filter(t => t.date === selectedDate).sort((a,b) => Number(a.done)-Number(b.done) || Number(b.priority === 'high')-Number(a.priority === 'high'))
  const activeTask = tasks.find(t => t.id === timer.selectedTaskId)
  const roomScene = determineScene(settings.scene, weather)
  const mood: Mood = moodOverride || (timer.phase === 'focus' && timer.running ? (activeTask ? 'typing' : 'reading') : timer.phase !== 'focus' ? 'stretch' : roomScene === 'night' ? 'sleepy' : 'idle')
  const showName = settings.nickname.trim() || '你'
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
    setChatDraft(''); setChatError('')
    setMoodOverride('chat')
    if (!settings.aiUrl.trim() || !settings.aiModel.trim()) {
      const answer = /累|困|休息/.test(content) ? '那就稍微休息一下吧。窗外的风也在等你呢。' :
        /学习|工作|专注|代码|任务/.test(content) ? '我们一起把这一小段时间认真过好喵。我会安静地陪着你。' :
        '喵呜～我在这里！想聊天的话随时可以找我。'
      setChat(previous => [...previous, {id:uid(),role:'assistant',content:answer}].slice(-100))
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
      setChat(previous => [...previous,{id:uid(),role:'assistant',content:answer}].slice(-100))
    } catch (error) {
      setChatError(error instanceof TypeError ? '网络请求失败。请检查网络、API 地址和服务商是否允许浏览器跨域（CORS）。' : error instanceof Error ? error.message : '请求失败')
    } finally { setChatLoading(false) }
  }

  return <div className={'app-shell accent-' + settings.accent}>
    <div className="mobile-bar"><button aria-label="切换导航" onClick={() => setMobileNav(!mobileNav)}><Home size={19}/></button><strong>MewNook</strong><span>🐾</span></div>
    {mobileNav && <div className="mobile-backdrop" onClick={() => setMobileNav(false)} />}
    <aside className={'sidebar' + (mobileNav ? ' open' : '')}>
      <div className="brand"><div className="brand-icon">🐾</div><div><strong>MewNook</strong><span>YOUR COZY CORNER</span></div></div>
      <div className="side-section-title">我的空间</div>
      <nav aria-label="页面导航">
        <NavButton active={view === 'home'} icon={<Home size={19}/>} label="陪伴工作台" onClick={() => {setView('home');setMobileNav(false)}}/>
        <NavButton active={view === 'tasks'} icon={<ListTodo size={19}/>} label="日程与任务" onClick={() => {setView('tasks');setMobileNav(false)}}/>
        <NavButton active={view === 'stats'} icon={<ChartNoAxesColumnIncreasing size={19}/>} label="专注统计" onClick={() => {setView('stats');setMobileNav(false)}}/>
      </nav>
      <div className="side-section-title side-later">偏好</div>
      <nav><NavButton active={view === 'settings'} icon={<Settings2 size={19}/>} label="设置" onClick={() => {setView('settings');setMobileNav(false)}}/></nav>
      <div className="sidebar-spacer"/>
      <div className="side-today">
        <div className="side-today-icon"><Sparkles size={19}/></div>
        <div className="side-today-title">今天的小成就</div>
        <strong>{todayMinutes}<small> 分钟</small></strong>
        <div className="side-progress"><span style={{width:Math.min(100,todayMinutes / 120 * 100) + '%'}}/></div>
        <p>再专注一点点，慢慢来就好 ♡</p>
      </div>
      <div className="side-footer"><span className="online-dot"/> 本地优先 · 自由自在</div>
    </aside>

    <div className="workspace">
      <main className="main-pane">
        <header className="page-head">
          <div><div className="eyebrow">{new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'long'}).format(new Date(now))}</div><h1>{view === 'home' ? greeting + '，' + showName + '。' : view === 'tasks' ? '日程与任务' : view === 'stats' ? '专注统计' : '偏好设置'}</h1>
          <p className="page-subtitle">{view === 'home' ? '欢迎回到属于你的小小角落。' : view === 'tasks' ? '给今天安排一些温柔又充实的事情。' : view === 'stats' ? '每一份认真的时间，都值得珍藏。' : '把这个小窝调整成你喜欢的样子。'}</p></div>
          <div className="weather-pill" title={weatherError ? '天气暂时不可用，场景仍可手动控制' : '天气由 Open-Meteo 提供'}><MapPin size={15}/><span>{weather ? weather.name : settings.city}</span><span className="weather-separator">·</span>{weather ? <><CloudRain size={15}/>{weather.temperature}° · {weatherDescription(weather.code)}</> : weatherError ? '天气离线' : '加载天气…'}</div>
        </header>

        {view === 'home' && <>
          <section className={'scene-card scene-' + roomScene}>
            <div className="scene-stars"/><div className="scene-light"/><div className="scene-window"><div className="scene-skyline"/><div className="scene-rain"/></div>
            <div className="scene-wall-art">✧</div><div className="scene-shelf"><span>▥</span><span>▤</span><span>✦</span></div>
            <div className="scene-lamp"/><div className="scene-table"/>
            <div className="scene-copy"><span className="scene-kicker"><span className="scene-kicker-dot"/> LITTLE MOMENTS, BIG DREAMS</span><h2>让今天，也成为<br/><em>温柔的一天。</em></h2><p>你的专属陪伴空间，<br/>和她一起学习、工作、发呆。</p><div className="scene-chips"><span><Sparkles size={13}/> {sceneName[settings.scene]}</span><span>♫ 慢慢来，不着急</span></div></div>
            <Companion mood={mood} phase={timer.phase}/>
            <div className="companion-bubble">{timer.running ? '嘘…我们一起认真工作喵 ♡' : timer.phase !== 'focus' ? '辛苦啦，休息一会儿吧！' : '今天想先做什么呢？'}</div>
            <div className="scene-controls">
              <button onClick={() => saveSettings({ scene: settings.scene === 'auto' ? 'rain' : settings.scene === 'rain' ? 'night' : 'auto' })} title="切换场景"><MoonStar size={17}/> 更换场景</button>
              <button onClick={() => setMoodOverride(m => m === 'happy' ? null : 'happy')} title="和猫娘互动"><Heart size={17}/> 摸摸头</button>
            </div>
          </section>
          <div className="dashboard-grid">
            <section className="panel timer-panel">
              <div className="panel-heading"><div><span className="section-icon lilac"><Clock3 size={18}/></span><strong>一起专注</strong></div><span className="muted-small">POMODORO</span></div>
              <div className="phase-switch">
                {(['focus','short','long'] as Phase[]).map(phase => <button key={phase} className={timer.phase === phase ? 'selected' : ''} onClick={() => selectPhase(phase)}>{phaseName[phase]}</button>)}
              </div>
              <div className="clock-display"><span>{timeLabel(remaining)}</span><svg viewBox="0 0 270 12" preserveAspectRatio="none"><rect width="270" height="12" rx="6" fill="#e8e7f1"/><rect width={270 * progress / 100} height="12" rx="6" fill="#8b98ce"/></svg></div>
              <div className="timer-actions"><button className="primary-button" onClick={toggleTimer}>{timer.running ? <Pause size={18}/> : <Play size={18} fill="currentColor"/>}{timer.running ? '暂停专注' : remaining < currentDuration ? '继续计时' : '开始专注'}</button><ButtonIcon title="重置当前计时" onClick={resetTimer}><RotateCcw size={18}/></ButtonIcon></div>
              <div className="timer-task"><span>本轮任务</span><select aria-label="本轮专注关联任务" value={timer.selectedTaskId || ''} onChange={e => setTimer(t => ({...t,selectedTaskId:e.target.value || null}))}><option value="">自由专注</option>{tasks.filter(t=>!t.done).map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></div>
            </section>

            <section className="panel today-panel">
              <div className="panel-heading"><div><span className="section-icon peach"><ListTodo size={18}/></span><strong>今日计划</strong></div><button className="text-link" onClick={() => {setSelectedDate(localDate());setView('tasks')}}>查看全部 <ChevronRight size={14}/></button></div>
              <div className="task-today-summary">已完成 <b>{completedToday}</b> / {todayTasks.length} 项任务</div>
              {todayTasks.length === 0 ? <div className="empty-mini">今天还没有任务喵。<br/>写下第一件想做的事吧。</div> :
                <div className="mini-tasks">{todayTasks.slice(0,4).map(t=><label key={t.id} className={'mini-task' + (t.done ? ' done' : '')}><input type="checkbox" checked={t.done} onChange={e=>updateTask(t.id,{done:e.target.checked})}/><span>{t.title}</span>{t.priority==='high' && <i className="priority-dot"/>}</label>)}</div>}
              <button className="add-task-link" onClick={() => {setSelectedDate(localDate());setView('tasks')}}><Plus size={16}/> 添加今日任务</button>
            </section>
          </div>
          <div className="dashboard-grid bottom-grid">
            <section className="panel mini-stats"><div className="panel-heading"><div><span className="section-icon blue"><ChartNoAxesColumnIncreasing size={18}/></span><strong>本周专注</strong></div><button className="text-link" onClick={()=>setView('stats')}>详细统计 <ChevronRight size={14}/></button></div><WeeklyChart sessions={sessions}/></section>
            <section className="panel gentle-note"><div className="quote-sparkle">✧</div><span>今日小贴士</span><p>不用每一分钟都充满效率。<br/>休息，也是认真生活的一部分。</p><small>WITH LOVE, MEWNOOK ♡</small></section>
          </div>
        </>}

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
        <footer className="content-footer"><span>MewNook · Made for little moments ✧</span><span>本地数据不会自动同步到云端</span></footer>
      </main>

      <aside className="companion-pane">
        <div className="side-widget-heading"><div><span className="section-icon lilac"><Heart size={18}/></span><strong>陪伴角落</strong></div><span className="connected-badge"><span/> {settings.aiUrl && settings.aiModel ? '自定义 API' : '离线陪伴'}</span></div>
        <div className="cat-profile"><div className="cat-avatar">🐱</div><div><b>小猫同学</b><span>{timer.running ? '正在陪你认真工作…' : '正在小窝里等你 ♡'}</span></div></div>
        <div className="chat-scroll" aria-live="polite">{chat.map(message=><div key={message.id} className={'chat-message '+message.role}>{message.role==='assistant'&&<span className="message-avatar">🐾</span>}<p>{message.content}</p></div>)}{chatLoading&&<div className="chat-message assistant"><span className="message-avatar">🐾</span><p>正在想怎么回答你…</p></div>}{chatError&&<div className="chat-error">{chatError}</div>}<div ref={chatBottomRef}/></div>
        <div className="chat-input"><input aria-label="给猫娘发送消息" maxLength={1600} value={chatDraft} onChange={e=>setChatDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void sendChat()}}} placeholder="和小猫说点什么…" /><button aria-label="发送消息" disabled={chatLoading||!chatDraft.trim()} onClick={()=>void sendChat()}><Send size={17}/></button></div>
        <div className="chat-disclaimer">{settings.aiUrl ? '自定义 API · Key 不保存在云端' : '当前为预设台词 · 设置中可连接 AI'}</div>
        <div className="aside-divider" />
        <div className="side-widget-heading"><div><span className="section-icon peach"><Headphones size={18}/></span><strong>声音空间</strong></div><button className="icon-button" title={ambientOn?'关闭环境音':'开启环境音'} onClick={()=>void toggleAmbient()}>{ambientOn?<Volume2 size={18}/>:<VolumeX size={18}/>}</button></div>
        <div className="ambience-list">{([
          {kind:'rain' as AmbientKind,name:'轻轻雨声',icon:<CloudRain size={18}/>},
          {kind:'wind' as AmbientKind,name:'窗边微风',icon:<Wind size={18}/>},
          {kind:'brown' as AmbientKind,name:'柔和底噪',icon:<Coffee size={18}/>}
        ]).map(item=><div className="ambience-row" key={item.kind}><span className="ambience-icon">{item.icon}</span><span>{item.name}</span><input aria-label={item.name+'音量'} type="range" min="0" max="100" value={ambientLevels[item.kind]} onChange={e=>levelChange(item.kind,Number(e.target.value))}/></div>)}</div>
        <button className={'sound-toggle'+(ambientOn?' active':'')} onClick={()=>void toggleAmbient()}>{ambientOn?<Pause size={16}/>:<Play size={16}/>} {ambientOn?'暂停环境音':'播放环境音'}</button>
        <div className="aside-divider"/>
        <div className="side-widget-heading"><div><span className="section-icon blue"><Music2 size={18}/></span><strong>我的音乐</strong></div></div>
        <label className="music-import"><Plus size={16}/> 选择本地音乐<input type="file" accept="audio/*,.flac" multiple hidden onChange={e=>loadTracks(e.target.files)}/></label>
        {tracks.length>0 ? <div className="music-player"><div className="track-name">♫ {tracks[trackIndex]?.name}</div><audio ref={musicRef} controls preload="metadata" src={tracks[trackIndex]?.url} onEnded={()=>setTrackIndex(i=>(i+1)%tracks.length)}/><div className="track-nav"><button onClick={()=>setTrackIndex(i=>(i+tracks.length-1)%tracks.length)}><ChevronLeft size={16}/> 上一首</button><span>{trackIndex+1}/{tracks.length}</span><button onClick={()=>setTrackIndex(i=>(i+1)%tracks.length)}>下一首 <ChevronRight size={16}/></button></div></div>
        :<div className="music-empty">支持本地音频，不上传服务器。<br/>更换或刷新页面需要重新选择文件。</div>}
        <div className="aside-bottom">✦ 愿每个普通的日子都闪闪发光</div>
      </aside>
    </div>
  </div>
}
