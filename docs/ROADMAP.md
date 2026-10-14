# MewNook development roadmap

## Stage 1: local-first usable prototype

- [x] v0.2 immersive full-screen virtual room UI, floating docks, slide-out panels, visual-novel dialogue and expandable chat.

- [x] Responsive cozy dashboard and dedicated tasks, statistics, settings views
- [x] Pomodoro with pause/resume, reload recovery and focus session history
- [x] Daily tasks, scheduled dates, completion, task selection
- [x] Local statistics, simple week chart, local JSON backup
- [x] Dynamic CSS room based on time/weather/manual scene selection
- [x] City weather via Open-Meteo with explicit credit and graceful fallback
- [x] Browser-synthesized rain/wind/brown-noise ambience
- [x] Local audio files (session only, not uploaded)
- [x] Offline scripted companion and optional direct OpenAI-compatible BYOK chat
- [x] Installable PWA build configuration and Workers Static Assets deployment
- [ ] GitHub Actions build verification / deployment after Cloudflare credentials are configured

## Stage 2: companion media and visual polish

- [x] Native three-layer night scene compositor using consistent virtual coordinates (background, sleepy companion, foreground occlusion).
- [x] Import night illustrations in settings and persist image Blobs locally in IndexedDB, with optional packaged defaults.
- [ ] Commit finalized image artwork to `public/assets/rooms/night/` when binary asset upload is available; downloadable pack prepared separately.

- [ ] Import and use the user's **six** consistent transparent-background portrait assets (current generated images are scene collages, not ready-to-layer portraits)
- [ ] Blend images with room layers, smooth transitions, click/hover expressions
- [ ] Focus/rest activity variations; additional outfits; accessible reduced-motion options
- [ ] Replace SVG prototype mascot when licensed image assets are ready

## Stage 3: richer routines

- [ ] Calendar time-blocks, recurring tasks, drag-and-drop scheduling
- [ ] IndexedDB for large data and music collections
- [ ] Cross-device sync (opt-in; later D1 / auth)
- [ ] Authorized streaming music providers
- [ ] Optional Workers AI relay with SSRF protection/auth/rate limits
- [ ] TTS, audio reactive lip-sync, Live2D renderer adapter

## Safety and operating principles

- Local first. No third-party analytics, registration or paid infrastructure needed.
- Never store user-supplied AI key on Cloudflare or in persistent localStorage.
- BYOK calls go straight from browser to provider; CORS support is required.
- Restrict provider URLs to HTTPS except loopback for local inference.
- Timer uses timestamps rather than interval counting and logs a completed work block once.
- Open-Meteo noncommercial usage and attribution are subject to their license.
