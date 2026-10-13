import type { Phase } from './model'

export type Mood = 'idle' | 'reading' | 'typing' | 'stretch' | 'chat' | 'sleepy' | 'happy'
export function Companion({ mood, phase }: { mood: Mood; phase: Phase }) {
  const smiling = mood === 'chat' || mood === 'happy' || mood === 'stretch'
  const sleepy = mood === 'sleepy'
  const eyeDown = mood === 'reading' || mood === 'typing'
  return (
    <div className={'companion companion-' + mood} aria-label="白发蓝瞳猫娘（当前为可替换的 SVG 原型）" role="img">
      <svg viewBox="0 0 380 490" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="hair" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#ffffff"/><stop offset=".55" stopColor="#e6e6f6"/><stop offset="1" stopColor="#b9bcd9"/>
          </linearGradient>
          <linearGradient id="hoodie" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#fffefc"/><stop offset="1" stopColor="#dce5f4"/>
          </linearGradient>
          <linearGradient id="skirt" x1="0" x2="1">
            <stop stopColor="#647aa8"/><stop offset=".6" stopColor="#9db6d9"/><stop offset="1" stopColor="#61769e"/>
          </linearGradient>
        </defs>
        {/* A thin tail, purposely unlike the earlier oversized plume. */}
        <path d="M249 345 C311 358 327 316 305 286 C297 277 287 278 282 284" fill="none" stroke="#b8bad0" strokeWidth="19" strokeLinecap="round"/>
        <path d="M249 345 C311 358 327 316 305 286 C297 277 287 278 282 284" fill="none" stroke="#f3eff8" strokeWidth="14" strokeLinecap="round"/>
        <path d="M108 237 Q65 305 72 420 Q75 454 119 443 Q130 392 146 344 L220 345 Q237 409 251 443 Q295 455 296 421 Q307 304 257 234Z" fill="url(#hair)" stroke="#c6c4df" strokeWidth="3"/>
        <path d="M136 356 L127 460 L167 460 L187 370Z" fill="#383d59"/>
        <path d="M212 356 L212 460 L253 460 L242 370Z" fill="#383d59"/>
        <path d="M122 451 Q121 469 112 474 L169 474 L168 454Z M210 454 L209 474 L271 474 Q257 465 252 451Z" fill="#262b41"/>
        <path d="M116 330 Q190 298 270 330 L284 382 Q190 399 101 382Z" fill="url(#skirt)" stroke="#5875a0" strokeWidth="3"/>
        <path d="M117 349 Q188 366 271 348 M109 371 Q187 388 280 371" fill="none" stroke="#d5def1" strokeWidth="3" opacity=".5"/>
        <path d="M118 245 Q190 221 253 245 Q285 279 267 356 Q190 376 106 353 Q95 275 118 245Z" fill="url(#hoodie)" stroke="#c5cde0" strokeWidth="3"/>
        <path d="M113 264 Q67 266 60 328 Q60 356 90 359 L131 333 L141 278Z" fill="url(#hoodie)" stroke="#c5cde0" strokeWidth="3"/>
        <path d="M260 263 Q310 273 319 326 Q322 354 287 358 L246 325Z" fill="url(#hoodie)" stroke="#c5cde0" strokeWidth="3"/>
        {mood === 'stretch'
          ? <><path d="M65 315 Q42 227 73 146" fill="none" stroke="#e7d6d3" strokeWidth="21" strokeLinecap="round"/><path d="M313 313 Q340 221 312 146" fill="none" stroke="#e7d6d3" strokeWidth="21" strokeLinecap="round"/></>
          : <><ellipse cx="87" cy="358" rx="18" ry="13" fill="#f0d5d1"/><ellipse cx="299" cy="357" rx="18" ry="13" fill="#f0d5d1"/></>}
        <path d="M149 240 Q189 285 225 240 L228 265 Q186 303 147 266Z" fill="#e9d3d4"/>
        <path d="M153 261 L186 280 L174 305 L141 287Z M219 261 L189 280 L202 305 L233 287Z" fill="#6f89b5" stroke="#4b668f" strokeWidth="2"/>
        <circle cx="188" cy="285" r="8" fill="#f4f2fa"/>
        {/* Large flowing hair and cat ears */}
        <path d="M86 184 Q60 105 91 48 L143 87 Q193 59 237 87 L288 44 Q317 127 282 185 L279 254 Q187 291 93 254Z" fill="url(#hair)" stroke="#bfc1dc" strokeWidth="3"/>
        <path d="M91 123 L93 52 L147 105Z M235 104 L286 51 L282 128Z" fill="#f5f0f7" stroke="#b9b9d4" strokeWidth="4"/>
        <path d="M106 109 L102 69 L135 108Z M252 108 L278 69 L275 109Z" fill="#f6cfd7" opacity=".8"/>
        <path d="M112 131 Q116 100 190 99 Q268 102 271 142 L270 192 Q263 244 191 253 Q111 243 109 187Z" fill="#f9e8e3" stroke="#e6d3d7" strokeWidth="2"/>
        <path d="M100 153 Q107 85 166 78 Q214 57 265 104 Q281 133 271 156 L251 136 L239 143 L231 119 L214 148 L191 122 L177 154 L157 138 L138 156 L127 135Z" fill="url(#hair)" stroke="#c5c5e0" strokeWidth="2"/>
        <path d="M114 157 Q87 180 98 261 Q109 278 127 271 L129 185Z M264 155 Q294 174 284 258 Q266 277 253 272 L249 181Z" fill="url(#hair)" stroke="#c5c5e0" strokeWidth="2"/>
        <ellipse cx="137" cy="198" rx="17" ry="11" fill="#f5a8b8" opacity=".32"/>
        <ellipse cx="242" cy="198" rx="17" ry="11" fill="#f5a8b8" opacity=".32"/>
        {sleepy
          ? <><path d="M136 183 Q155 190 169 180 M209 180 Q229 190 246 183" fill="none" stroke="#7081ae" strokeWidth="5" strokeLinecap="round"/></>
          : <>
            <ellipse cx="155" cy={eyeDown ? 190 : 185} rx="15" ry={eyeDown ? 15 : 20} fill="#fff"/>
            <ellipse cx="227" cy={eyeDown ? 190 : 185} rx="15" ry={eyeDown ? 15 : 20} fill="#fff"/>
            <ellipse cx="155" cy={eyeDown ? 194 : 187} rx="10" ry={eyeDown ? 11 : 16} fill="#5b9fce"/>
            <ellipse cx="227" cy={eyeDown ? 194 : 187} rx="10" ry={eyeDown ? 11 : 16} fill="#5b9fce"/>
            <ellipse cx="152" cy="179" rx="4" ry="5" fill="#fff"/><ellipse cx="224" cy="179" rx="4" ry="5" fill="#fff"/>
            <path d="M138 169 Q151 162 171 172 M211 172 Q225 162 244 169" stroke="#616586" strokeWidth="4" strokeLinecap="round" fill="none"/>
          </>}
        <path d={smiling ? 'M178 216 Q191 230 205 216' : sleepy ? 'M185 214 Q190 236 198 214' : 'M183 217 Q190 222 198 217'} fill="none" stroke="#ae8291" strokeWidth="3" strokeLinecap="round"/>
        <path d="M125 127 l-10 14 l14 8 l9 -13Z" fill="#7a9cc7"/>
        <path d="M252 127 l10 14 l-14 8 l-9 -13Z" fill="#7a9cc7"/>
        {(mood === 'reading' || mood === 'typing') && <g>
          <path d="M137 307 Q180 290 190 307 Q223 290 252 308 L253 362 Q222 345 189 365 Q164 347 131 362Z" fill={mood === 'typing' ? '#7287ae' : '#f6efdf'} stroke="#7184ae" strokeWidth="4"/>
          <path d="M190 307 L189 365" stroke="#9eacc6" strokeWidth="3"/>
        </g>}
        {phase !== 'focus' && mood === 'happy' && <><path d="m80 190 12 -10 M95 211 l-15 6" stroke="#f8c66e" strokeWidth="4"/><path d="m288 193 12 -10 M288 211 l15 8" stroke="#f8c66e" strokeWidth="4"/></>}
      </svg>
    </div>
  )
}
