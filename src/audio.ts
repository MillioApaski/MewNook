// No third-party audio and no network: synthesize low-volume ambient noise on the user's device.
export type AmbientKind = 'rain' | 'wind' | 'brown'

export class AmbientEngine {
  private context: AudioContext | null = null
  private sources: AudioBufferSourceNode[] = []
  private gains: Partial<Record<AmbientKind, GainNode>> = {}
  private volume: Record<AmbientKind, number> = { rain: 0.23, wind: 0.08, brown: 0 }
  private master: GainNode | null = null

  async start() {
    if (this.context) { await this.context.resume(); return }
    const context = new AudioContext()
    this.context = context
    const length = context.sampleRate * 3
    const white = context.createBuffer(1, length, context.sampleRate)
    const brown = context.createBuffer(1, length, context.sampleRate)
    const a = white.getChannelData(0)
    const b = brown.getChannelData(0)
    let prev = 0
    for (let i = 0; i < length; i++) {
      const noise = Math.random() * 2 - 1
      a[i] = noise
      prev = (prev + noise * 0.02) / 1.02
      b[i] = prev * 3.4
    }
    const master = context.createGain()
    master.gain.value = 0.35
    master.connect(context.destination)
    this.master = master
    for (const kind of ['rain', 'wind', 'brown'] as AmbientKind[]) {
      const source = context.createBufferSource()
      source.buffer = kind === 'brown' ? brown : white
      source.loop = true
      const filter = context.createBiquadFilter()
      filter.type = kind === 'rain' ? 'highpass' : 'lowpass'
      filter.frequency.value = kind === 'rain' ? 450 : kind === 'wind' ? 320 : 160
      const gain = context.createGain()
      gain.gain.value = this.volume[kind]
      source.connect(filter).connect(gain).connect(master)
      source.start()
      this.sources.push(source)
      this.gains[kind] = gain
    }
    await context.resume()
  }
  setVolume(kind: AmbientKind, value: number) {
    this.volume[kind] = Math.max(0, Math.min(value, 1))
    this.gains[kind]?.gain.setTargetAtTime(this.volume[kind], this.context?.currentTime ?? 0, 0.06)
  }
  async stop() {
    if (!this.context) return
    for (const source of this.sources) { try { source.stop() } catch { /* stopped */ } }
    this.sources = []
    await this.context.close()
    this.context = null
    this.master = null
    this.gains = {}
  }
}
