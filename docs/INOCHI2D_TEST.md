# MewNook · Inochi2D runtime experiment

## Scope and non-goals

This is an opt-in **genuine Inochi2D** WebGL2/WASM experiment with a third-party
rigged sample model. It does NOT generate a Cubism file, does NOT represent a
finished custom MewNook character, and does NOT replace default PNG artwork.

## Provenance / licenses

Upstream host: https://github.com/shinshin86/aituber-onair
Pinned commit: `d8236762cc45d8909164321b9a7f80687cec827d`
Sample path: `packages/core/examples/react-inochi2d-app/public/inochi2d/`

- Browser bridge code: AITuber OnAir, MIT, copyright Yuki Shindo (2025).
- Browser runtime: Rust Inox2D BSD-2-Clause and further dependencies; see
  `public/inochi2d-test/runtime/THIRD-PARTY-NOTICES.md`.
- Test model Aka: creator **seagetch**, CC BY 4.0:
  https://github.com/Inochi2D/example-models
  This is a modified demo rig containing additional idle and reaction motions;
  see `public/inochi2d-test/models/Aka.ATTRIBUTION.md`.

We only download the listed source assets at a pinned commit and require exact
Git blob SHA-1 and byte length before writing any file. No arbitrary model URL
is accepted from users, and testing remains off by default.

## Run

```bash
npm install
npm run prepare:inochi
npm run dev
```

Open Settings > Virtual Room > Inochi2D Test Mode.
The download is ~18 MB for the rig and ~1 MB for the runtime, but is only
requested by the client when the user enables testing.
WebGL2 is required. The original PNG layer remains visible until the model
successfully loads and is restored on failure.

Only runtime behavior is verified by the default CI build; final WebGL visual
quality needs a real-browser screenshot/regression test.

## Final model workflow (not yet done)

1. Create a specifically licensed **original** layered PSD source for the
   white-haired blue-eyed MewNook companion.
2. Use Inochi Creator to build meshes and bind blink, body breath, gaze,
   head turn, ears, tail, focus reading/writing, rest and reaction parameters.
3. Export a versioned `.inx` or `.inp` and inspect it in the browser with
   the runtime adapter before changing the default model setting.
4. Keep explicit artifact licenses and fallback assets within the repo.
