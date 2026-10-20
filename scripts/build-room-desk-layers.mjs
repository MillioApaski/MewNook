import{readFileSync,writeFileSync}from'node:fs'
import{createHash}from'node:crypto'

// A standalone image per scene. Original raster pixels are embedded unchanged;
// SVG supplies the transparent cutout, never a painted replacement or a fade.
for(const scene of['day','rain','sunset','night']){
 const input=`public/assets/rooms/${scene}/${scene==='day'?'background':'foreground'}.webp`
 const source=readFileSync(input),digest=createHash('sha256').update(source).digest('hex')
 const content=scene==='day'
  ? '<defs><clipPath id="desk"><path d="M0 686 L1672 743.684 L1672 941 L0 941 Z"/></clipPath></defs><g clip-path="url(#desk)">'
  : '<defs><filter id="hard-alpha" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncA type="discrete" tableValues="0 1"/></feComponentTransfer></filter></defs><g filter="url(#hard-alpha)">'
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1672" height="941" viewBox="0 0 1672 941" data-extraction="hard-alpha"><metadata>Original pixels: ${input}; sha256:${digest}. Independent desk foreground; no feather or gradient.</metadata>${content}<image width="1672" height="941" href="data:image/webp;base64,${source.toString('base64')}"/></g></svg>\n`
 writeFileSync(`public/assets/rooms/${scene}/desk.svg`,svg)
 console.log(`${scene}: independent desk, ${source.length} original bytes`)
}
