export const characterDefaults = {
  inochiTestMode: true,
  inochiScale: 0.32,
  inochiModel: 'v4' as const,
  inochiModelRevision: 1
}

// Apply the approved character once, including installations with the old opt-in default.
// Subsequent user choices (including disabling animation) remain authoritative.
export function migrateCharacterSettings(saved: Record<string, unknown>) {
  return saved.inochiModelRevision === characterDefaults.inochiModelRevision
    ? saved : {...saved, ...characterDefaults}
}
