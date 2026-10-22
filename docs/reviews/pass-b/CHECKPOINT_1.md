# 2.9.9 Pass B: design foundation and selected UI audio

Baseline: development at `80df4d745ea3b0b0549bb15893be0247752c45ab`.
The untouched baseline passed 503 tests in 233.82 seconds. Version remains 2.9.9;
the installed/root EXEs and Start Menu route remain held for owner review.

DESIGN.md, AUDIO_DESIGN.md and docs/design establish the preserved modern 2.9.9
interface, future Cathedral direction, reference interpretation, checklist and
private-media recovery contract. The supplied Variant D PNG was found in the
repository despite its missing Downloads path and is tracked unchanged.

All seven named selected WAV roles are connected through AudioRouter/ui.feedback.
Save belongs to successful manual writes, errors to failed/rejected operations,
and panel close is distinct from application exit. UI transactions choose a
single semantic cue. Separate reserved pools protect editor music and opening
audio. Ordinary map clicks use the selected button; retained map music and
rollover/plan/completion media stay intact. World Map has a brief cancellable
cover/reveal and immediate reduced-motion path.

Eleven originals, including four unassigned extras, remain in Sounds/ and have
byte-identical permanent copies. The ZIP round trip is hash verified at
`.qa/pass-b/selected-audio-originals.zip`; this is a local recovery copy, not an
off-device backup. Standalone source redistribution is not inferred from private
compiled-release permission. All media stay ignored; inventory/recipes are tracked.

Focused audio/UI regression: 29 passed. The expanded suite ran 510 checks:
504 passed, four failures exposed missing-asset-owner assumptions in lightweight
test harnesses, and two correctly rejected stale prepared tutorials. The guards
were repaired and exact prepared data rebaked. All affected checks then passed:
41 action/maintenance/audio tests and both prepared-tutorial tests. Evidence is
under `.qa/pass-b/` (`feedback-before.log`, `feedback-after.log`,
`checkpoint1-tests.log`, `checkpoint1-fixes.log`, `prepared-checkpoint1.log`).

Seven actual decoded SDL cues, event priority, pool saturation, missing-media
behavior, hash validation, real save/failure, close, map cancel/reduced motion and
lifecycle routing are covered. This is automated playback, not human listening
approval. Shutdown uses a bounded short tail of the original recording; listening
review remains required. Final full-suite, rendering, packaging and playback
evidence will accompany checkpoint 2; this source checkpoint is not an installed
release or a claim that the known camera-performance holds are resolved.
