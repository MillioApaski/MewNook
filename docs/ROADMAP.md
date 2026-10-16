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

- [x] Temporarily show Galgame dialogue (6.5 seconds), reveal it for new messages and focus-cycle notifications, and retain expanded chat until dismissed.
- [x] Switch actual bundled catgirl artwork on focus (reading or typing) with manual selection and auto task-aware pose, across all four rooms.

- [x] Daytime room + sitting idle character + matching desk foreground bundled in public/assets/rooms/day/.
- [x] Sunset and rainy room, character, desk foreground bundled in public/assets/rooms/sunset/ and public/assets/rooms/rain/; all four scene modes now use illustration layers.

- [x] Native three-layer night scene compositor using consistent virtual coordinates (background, sleepy companion, foreground occlusion).
- [x] Include actual day and night WebP images in the repository and use static assets, without manual scene import.

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

## Phase 3C: AI companion (ahead of Live2D)

- [x] Browser-side OpenAI compatible SSE streaming, with non-streaming option, AbortController cancel and explicit retry.
- [x] Bounded recent conversation context and user-configurable output-token cap.
- [x] Local editable companion-memory notes and user-triggered API memory summarization (never silent paid calls).
- [x] Opt-in foreground-only proactive greetings, local free-by-default and separate AI opt-in with interval and daily budget.
- [ ] Add cross-tab request coordination and provider token-usage metrics if strict multi-tab cost accounting becomes necessary.
- [ ] Real-browser tests against chosen user's AI provider (CORS/stream format varies).
- [ ] Defer Live2D actions, expressions and scene animations to the Live2D milestone; do final PWA optimization afterwards.

## Inochi2D runtime experiment

- [x] Select open Inochi2D runtime with pinned SHA-verified WebGL2/WASM dependencies.
- [x] Add **opt-in** Inochi2D prototype and keep PNG default/fallback.
- [x] Adapt rendering into the existing background → character → foreground order; camera scale adjustable.
- [x] Attribute the temporary CC BY 4.0 Aka test rig and bundled third-party runtime licenses.
- [ ] Validate actual rendering / animation / click interactions in a deployed browser.
- [x] Generate a minimal original MewNook .inx puppet from existing artwork, with real textured meshes and 8 parameter bindings; verify its parsing in Chromium.
- [ ] Refine the new 14-layer white-haired catgirl illustration: paint hidden parts, adjust vertex meshes and rig it manually in Inochi Creator to replace the programmatic prototype.
- [ ] Integrate mature focus/rest/chat behavior after model action names are confirmed.
- [x] Bound text-driven mouth animation to new dialogue and streaming output; resume focus/rest/night/idle afterwards, including cancel/error paths. This is not audio lip-sync or a finished action rig.

## Phase 2 rig milestone
- [x] Replace rectangular eye snippets with bounded feathered ellipses and reconstructed face behind eyes.
- [x] Introduce distinct closed eyelid line meshes, mouth art, and state parameters.
- [x] Add generated model validation and browser loading smoke test.
- [ ] Full hand-painted layered source with concealed faces and individually deformable eyelids in Inochi Creator.
- [ ] Real motion clips and visual baseline screenshot comparison on desktop and phone.

## Inochi2D v3 multi-vertex deform milestone

- [x] Subdivide hair, tail, eyes, and eyelids into textured grid ArtMeshes.
- [x] Use native INX `deform` keyframe tracks with per-vertex displacements.
- [x] Integrate animation tick with focus, rest, chat, sleepy, and touch states.
- [x] Add structural tests for native deformation keyframe tracks.
- [x] Verify native per-vertex deform in Playwright Chromium screenshots with position fallback disabled.
- [ ] Merge new portrait layered source into repository and manually repaint concealed artwork.
- [ ] Finish manually authored Inochi Creator motion curves and visual proof across four rooms.

- [x] Correct Inox2D zsort and premultiplied-alpha exports; validate nonzero pixels for v3 hair/tail and blinking.
- [x] Make v3 the opt-in experiment model with v2 fallback, retaining PNG as site-wide default.
- [ ] Integrate the separately created original layered portrait after manual overpaint and fine mesh work.
