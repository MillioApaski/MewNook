/**
 * Vendor a pinned, permissively licensed Inochi2D WebGL2 sample runtime and
 * the CC BY 4.0 Aka sample rig into MewNook for *experimental* testing.
 *
 * Uses upstream Git blob SHA-1 checks. A mismatch fails closed; there are no
 * rolling tags or runtime CDN dependencies. Run: npm run prepare:inochi
 */
import {createHash} from 'node:crypto'
import {mkdir, readFile, writeFile} from 'node:fs/promises'
import {join, dirname} from 'node:path'

const repository = 'shinshin86/aituber-onair'
const revision = 'd8236762cc45d8909164321b9a7f80687cec827d'
const prefix = 'packages/core/examples/react-inochi2d-app/public/inochi2d/'
const files = [
  ['runtime/inochi_bridge.js','a82da73194f7cde9fe131a626578b74478e610c2',119059],
  ['runtime/inochi2d.js','d3d3e2dd04ddd6e407b569e61eed48d5cb30b2c3',44289],
  ['runtime/inochi2d_bg.wasm','cd326981297a2ccc63ebb1f885bea03e895236a9',911722],
  ['runtime/secondary_motion.js','f89b2ed2ac0ab73eba37e1742ef48cc3fac64b0a',4026],
  ['runtime/THIRD-PARTY-NOTICES.md','f420315961d69c488a6fb63363b61d12501804f4',4067],
  ['models/Aka.inx','79a5f77c97bb066f5da772425e7fb1d9b4bee750',17889230],
  ['models/Aka.ATTRIBUTION.md','3426eaa2b84f6e0d27cd4727b7d1bcea5f80221d',909],
]
const base = join(process.cwd(),'public','inochi2d-test')
const blobId = data => createHash('sha1').update('blob '+data.length+'\0').update(data).digest('hex')
for(const [path, sha, size] of files) {
  const dest = join(base,path)
  let ok = false
  try {
    const existing = await readFile(dest)
    ok = existing.length === size && blobId(existing) === sha
  } catch {/* not yet downloaded */}
  if(ok) {console.log('cached:',path);continue}
  const source = 'https://raw.githubusercontent.com/'+repository+'/'+revision+'/'+prefix+path
  console.log('fetching:',path)
  const resp=await fetch(source,{signal:AbortSignal.timeout(120000)})
  if(!resp.ok) throw new Error(path+': HTTP '+resp.status)
  const bytes=Buffer.from(await resp.arrayBuffer())
  if(bytes.length!==size || blobId(bytes)!==sha)throw new Error('Upstream integrity mismatch for '+path)
  await mkdir(dirname(dest),{recursive:true})
  await writeFile(dest,bytes)
}
console.log('Inochi2D experimental assets verified from pinned upstream revision.')
