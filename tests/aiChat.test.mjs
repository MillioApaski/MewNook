import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import ts from 'typescript'

const source = await readFile(new URL('../src/aiChat.ts', import.meta.url), 'utf8')
const js = ts.transpileModule(source, {compilerOptions:{
  module:ts.ModuleKind.ES2022, target:ts.ScriptTarget.ES2022
}}).outputText
const {chatEndpoint, chatContext, boundedOutputTokens, requestAI} =
  await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'))

const defaults = (signal = new AbortController().signal) => ({
  url:'https://example.org/v1',model:'dummy',key:'test-key',
  messages:[{role:'system',content:'Be concise'},{role:'user',content:'hello'}],
  maxTokens:300,streaming:true,signal
})
async function withFetch(mock,fn){
  const previous=globalThis.fetch
  globalThis.fetch=mock
  try{return await fn()} finally{globalThis.fetch=previous}
}
const jsonResponse = (answer) => new Response(JSON.stringify({choices:[{message:{content:answer}}]}),
  {status:200,headers:{'content-type':'application/json'}})

test('sanitizes endpoint scheme and path',()=>{
  assert.equal(chatEndpoint('https://example.org/v1'),'https://example.org/v1/chat/completions')
  assert.equal(chatEndpoint('https://example.org/v1/chat/completions'),'https://example.org/v1/chat/completions')
  assert.equal(chatEndpoint('http://localhost:1234/v1'),'http://localhost:1234/v1/chat/completions')
  assert.throws(()=>chatEndpoint('http://example.org/v1'),/HTTPS/)
  assert.throws(()=>chatEndpoint('https://example.org/v1?token=private'),/查询参数/)
})
test('bounds text context and max output token control',()=>{
  const history=Array.from({length:18},(_,i)=>({id:String(i),role:i%2?'assistant':'user',content:'m'+i}))
  assert.equal(chatContext(history,6).length,6)
  assert.equal(chatContext(history,6)[0].content,'m12')
  assert.equal(boundedOutputTokens(0),120)
  assert.equal(boundedOutputTokens(99999),2048)
})
test('handles a nonstreaming JSON reply without duplicate HTTP calls',async()=>{
  let called=0, body
  await withFetch(async (_url,options)=>{
    called++;body=JSON.parse(options.body)
    assert.equal(options.headers.Authorization,'Bearer test-key')
    return jsonResponse('好的喵。')
  },async()=>{
    const answer=await requestAI({...defaults(),streaming:false})
    assert.equal(answer,'好的喵。')
  })
  assert.equal(called,1)
  assert.equal(body.stream,false)
  assert.equal(body.max_tokens,300)
})
test('accepts JSON reply even when streaming requested', async()=>{
  await withFetch(async()=>jsonResponse('JSON fallback'), async()=>{
    assert.equal(await requestAI(defaults()),'JSON fallback')
  })
})
test('parses fragmented SSE UTF-8 without dropping or duplicating characters',async()=>{
  const events=[
    'data: '+JSON.stringify({choices:[{delta:{content:'猫娘'}}]})+'\n\n',
    'data: '+JSON.stringify({choices:[{delta:{content:'在读书。'}}]})+'\n\n',
    'data: [DONE]\n\n'
  ].join('')
  const bytes=new TextEncoder().encode(events)
  const parts=[]
  for(let i=0;i<bytes.length;i+=3)parts.push(bytes.slice(i,i+3))
  const response = new Response(new ReadableStream({start(c){
    for(const p of parts)c.enqueue(p)
    c.close()
  }}),{headers:{'content-type':'text/event-stream'}})
  let partials=[]
  await withFetch(async()=>response,async()=>{
    const answer=await requestAI({...defaults(),onDelta:s=>partials.push(s)})
    assert.equal(answer,'猫娘在读书。')
  })
  assert.deepEqual(partials,['猫娘','猫娘在读书。'])
})
test('provider HTTP errors are surfaced and are not retried automatically',async()=>{
  let attempts=0
  await withFetch(async()=>{attempts++;return new Response(JSON.stringify({error:{message:'quota'}}),{status:429,headers:{'content-type':'application/json'}})},async()=>{
    await assert.rejects(()=>requestAI(defaults()),/HTTP 429.*quota/)
  })
  assert.equal(attempts,1)
})
test('aborting pending fetch rejects request',async()=>{
  const controller=new AbortController()
  await withFetch((_url,{signal})=>new Promise((_,reject)=>{
    signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')))
  }),async()=>{
    const promise=requestAI(defaults(controller.signal))
    controller.abort()
    await assert.rejects(promise, e=>e.name==='AbortError')
  })
})
