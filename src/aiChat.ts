import type { ChatMessage } from './model'

export interface AIMessage { role: 'system' | 'user' | 'assistant'; content: string }
export interface AIConfig {
  url: string
  model: string
  key: string
  messages: AIMessage[]
  maxTokens: number
  streaming: boolean
  signal: AbortSignal
  onDelta?: (text: string) => void
}

export function chatEndpoint(raw: string): string {
  const url = new URL(raw.trim())
  const host = url.hostname.replace(/^\[|\]$/g, '').toLowerCase()
  const local = host === 'localhost' || host === '127.0.0.1' || host === '::1'
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && local))
    throw new Error('API 地址必须使用 HTTPS；只有本地回环地址允许 HTTP')
  if (url.username || url.password || url.search || url.hash)
    throw new Error('API 地址不应包含账户、查询参数或锚点')
  const path = url.pathname.replace(/\/+$/, '')
  if (!path.endsWith('/chat/completions')) url.pathname = path + '/chat/completions'
  return url.toString()
}

export function chatContext(history: ChatMessage[], maxTurns: number): AIMessage[] {
  const count = Math.max(2, Math.min(30, Math.round(maxTurns)))
  const recent = history.slice(-count)
  const result: AIMessage[] = []
  let remaining = 12000
  // Prefer the most recent context and never cut surrogate pairs in the middle.
  for (let i = recent.length - 1; i >= 0; i--) {
    const message = recent[i]
    if (!['user', 'assistant'].includes(message.role) || !message.content.trim() || remaining < 120) break
    const safe = Array.from(message.content).slice(-Math.min(4000, remaining)).join('')
    remaining -= safe.length
    result.unshift({role: message.role, content: safe})
  }
  return result
}

export function boundedOutputTokens(value: number): number {
  return Number.isFinite(value) ? Math.max(120, Math.min(2048, Math.round(value))) : 600
}

function textOf(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(part => {
    if (!part || typeof part !== 'object') return ''
    const item = part as {text?: string; type?: string}
    return typeof item.text === 'string' ? item.text : ''
  }).join('')
  return ''
}
function extract(json: unknown): string {
  const data = json as { choices?: {delta?: {content?: unknown};message?: {content?: unknown}}[] }
  return textOf(data?.choices?.[0]?.delta?.content ?? data?.choices?.[0]?.message?.content)
}

/**
 * Stream OpenAI-compatible SSE without making a second paid request.
 * Handles split UTF-8 bytes, CRLF line endings, and multiple events per chunk.
 */
export async function requestAI(config: AIConfig): Promise<string> {
  const response = await fetch(chatEndpoint(config.url), {
    method: 'POST',
    signal: config.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(config.key ? {Authorization: 'Bearer ' + config.key} : {})
    },
    body: JSON.stringify({
      model: config.model,
      stream: config.streaming,
      temperature: 0.8,
      max_tokens: boundedOutputTokens(config.maxTokens),
      messages: config.messages
    })
  })
  if (!response.ok) {
    let detail = ''
    try {
      const json = await response.json() as {error?: {message?: string}}
      detail = json.error?.message?.slice(0, 160) || ''
    } catch { /* no response body */ }
    throw new Error('API HTTP ' + response.status + (detail ? '：' + detail : '。请检查模型、Key、额度或流式支持'))
  }
  if (config.signal.aborted) throw new DOMException('Aborted', 'AbortError')
  const contentType = response.headers.get('content-type') || ''
  if (!config.streaming || contentType.includes('application/json') || !response.body) {
    const answer = extract(await response.json()).trim()
    if (!answer) throw new Error('模型没有返回可显示的文字')
    config.onDelta?.(answer)
    return answer
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = '', answer = '', done = false
  const append = (part: string) => {
    if (!part) return
    answer += part
    if (answer.length > 32000) throw new Error('回复过长，已停止接收')
    config.onDelta?.(answer)
  }
  const processBlock = (block: string) => {
    const data = block.split('\n').map(line => line.trimStart())
      .filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n')
    if (!data) return
    if (data === '[DONE]') { done = true; return }
    let json: unknown
    try { json = JSON.parse(data) } catch { return }
    const typed = json as {error?: {message?: string}}
    if (typed?.error) throw new Error(typed.error.message || '流式请求失败')
    append(extract(json))
  }
  try {
    while (!done) {
      const {value, done: ended} = await reader.read()
      if (ended) break
      buffer += decoder.decode(value, {stream: true}).replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      let index: number
      while ((index = buffer.indexOf('\n\n')) >= 0) {
        processBlock(buffer.slice(0, index))
        buffer = buffer.slice(index + 2)
        if (done) break
      }
      if (buffer.length > 100000) throw new Error('流式响应数据格式异常')
    }
    buffer += decoder.decode()
    if (!done && buffer.trim()) processBlock(buffer)
    if (config.signal.aborted) throw new DOMException('Aborted', 'AbortError')
    if (!answer.trim()) throw new Error('流式请求没有返回文本。可尝试关闭流式回复')
    return answer.trim()
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
