import { useEffect, useRef, useState } from 'react'

export type NightLayer = 'background' | 'character' | 'foreground'
export const NIGHT_LAYERS: NightLayer[] = ['background', 'character', 'foreground']
export const NIGHT_ASSET_LABELS: Record<NightLayer, string> = {
  background: '夜间房间背景', character: '困倦猫娘立绘', foreground: '桌面前景遮挡'
}
type LayerUrls = Record<NightLayer, string | null>
const empty: LayerUrls = {background: null,character: null,foreground: null}
const DATABASE = 'mewnook-scene-assets'
const STORE = 'night-scene'
const MAX_BYTES = 16 * 1024 * 1024

function openDatabase(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') return Promise.reject(new Error('浏览器未启用 IndexedDB'))
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(new Error('打开本地素材存储失败'))
  })
}

async function readStored(db: IDBDatabase, key: string): Promise<Blob | undefined> {
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE, 'readonly').objectStore(STORE).get(key)
    request.onsuccess = () => resolve(request.result instanceof Blob ? request.result : undefined)
    request.onerror = () => reject(new Error('读取本地素材失败'))
  })
}

async function writeStored(db: IDBDatabase, key: string, file: Blob | null): Promise<void> {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE, 'readwrite')
    const store = transaction.objectStore(STORE)
    if (file) store.put(file, key)
    else store.delete(key)
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(new Error('保存素材失败，可能是设备存储空间不足'))
    transaction.onabort = () => reject(new Error('素材保存被中断'))
  })
}

async function packagedUrl(layer: NightLayer): Promise<string | null> {
  // Workers SPA fallback can respond with index.html for a missing asset.
  const path = '/assets/rooms/night/' + layer + '.webp'
  try {
    const response = await fetch(path, { method: 'HEAD' })
    return response.ok && (response.headers.get('content-type') || '').startsWith('image/') ? path : null
  } catch { return null }
}

export function useNightSceneAssets() {
  const [urls, setUrls] = useState<LayerUrls>(empty)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const dbRef = useRef<Promise<IDBDatabase> | null>(null)
  const generatedRef = useRef<Partial<Record<NightLayer, string>>>({})
  const getDb = () => {
    if (!dbRef.current) dbRef.current = openDatabase()
    return dbRef.current
  }

  useEffect(() => {
    let cancelled = false
    void (async () => {
      let db: IDBDatabase | null = null
      try { db = await getDb() } catch { /* packaged assets still work */ }
      const results = await Promise.all(NIGHT_LAYERS.map(async layer => {
        let file: Blob | undefined
        if (db) try { file = await readStored(db, layer) } catch { /* fallback */ }
        if (file) {
          const url = URL.createObjectURL(file)
          if (cancelled) { URL.revokeObjectURL(url); return [layer,null] as const }
          generatedRef.current[layer] = url
          return [layer,url] as const
        }
        return [layer,await packagedUrl(layer)] as const
      }))
      if (!cancelled) {
        setUrls(Object.fromEntries(results) as LayerUrls)
        setLoading(false)
      }
    })()
    return () => {
      cancelled = true
      for (const url of Object.values(generatedRef.current)) if (url) URL.revokeObjectURL(url)
      generatedRef.current = {}
    }
  }, [])

  async function importLayer(layer: NightLayer, file: File) {
    setError('')
    if (!['image/png','image/webp','image/jpeg'].includes(file.type))
      throw new Error('请使用 PNG、WebP 或 JPEG 图片')
    if (file.size > MAX_BYTES) throw new Error('单张素材不能超过 16 MB')
    const db = await getDb()
    await writeStored(db, layer, file)
    const url = URL.createObjectURL(file)
    const old = generatedRef.current[layer]
    generatedRef.current[layer] = url
    setUrls(current => ({...current,[layer]:url}))
    if (old) URL.revokeObjectURL(old)
  }

  async function clearLayer(layer: NightLayer) {
    setError('')
    const db = await getDb()
    await writeStored(db, layer, null)
    const path = await packagedUrl(layer)
    const old = generatedRef.current[layer]
    delete generatedRef.current[layer]
    setUrls(current => ({...current,[layer]:path}))
    if (old) URL.revokeObjectURL(old)
  }

  return { urls, loading, error, setError, importLayer, clearLayer }
}
