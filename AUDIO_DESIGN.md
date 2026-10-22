# Bloc Fantôme audio specification

The permanent sonic direction is musical, subtle, tactile and piano-oriented,
with a faint cathedral quality. Silence is part of the design. No generic sci-fi
chirps, repetitive beeps, gratuitous reverb or invented alien oscillators.
Version 2.9.9 uses the owner's selected recordings; 3.0 retains this discipline.

## Selected semantic events

Original paths below are relative to `Assets/Sound Hub/ui/selected/`. Originals are
unchanged in `Sounds/`; full characteristics and hashes are in
[selected-audio.json](docs/design/selected-audio.json).

| Role | File | Trigger | Gain before router |
| --- | --- | --- | --- |
| Boot | bootUp.wav | First visible swamp splash, before bulk assets | 0.76 |
| Shutdown | shutDown.wav | Normal application exit, distinct from panel close | 0.76 |
| World Map | worldMap.wav | Start cartographic unfolding | 0.82 |
| Save | save.wav | Confirmed successful manual write, including Ctrl+S | 0.78 |
| Error | error.wav | Failed operation or explicit rejection | 0.80 |
| Button | pressButton.wav | Deliberate ordinary UI activation | 0.90 |
| Close | Code/ui/audio/close-short.wav | Dismiss/back/collapse; Library opening and closing | 0.72 |

No save cue for opening/cancelling a dialog or background autosaves. Errors are
not hover warnings; throttle repeats to at most one per 650 ms. No default hover,
focus, scrolling, typing or idle cue. Extras are catalogued, unassigned proposals.
Application shutdown has a bounded 1.8-second event-pumped Goodbye, fading over
the final 300 ms. Escape, Enter, Space, click or window close stops the cue and
skips the composition immediately. The original 5.31-second file stays intact.

The close derivative retains 0.040–0.440 seconds of the original, applies gain
1.25, a 3 ms attack ramp and a 150 ms cosine fade. Duration is 400 ms; measured
peak is 0.4653 full scale with zero clipped samples. Reproduce it with
`Code/tools/derive_close_cue.py`; the adjacent JSON records source/output hashes
and the recipe. The original 3.69-second WAV is untouched. Library opening and
closing each produce one short close cue, coalescing any enclosing button cue.
The ordinary button gain rises from 0.80 to 0.90 without changing ambient routing.
Timing, musical preference and balance still require owner headphone/speaker review.

## Routing and volume

`engine.audio.AudioRouter` owns bounded pools. `ui.feedback` loads the selected
recordings and coalesces nested input actions to the highest semantic priority:
error, save, map, close, button. Lifecycle is separate. A dispatch batch never
adds a generic click underneath a more specific cue. Legacy select/open map to
button; cancel maps to close; focus stays silent. Audio failures log once and do
not prevent development startup. Release validation rejects missing/hash-changed
selected originals, including preserved extras.

Channel allocation: buttons/retained map cues 0–1; weather 2–3; ambient 4–7;
world effects 8–23; horror 24–25; portal 26; semantic UI 27–28; lifecycle 29;
opening piano 30; editor music 31; opening-specific pools begin at 32. Reserve
all named channels from automatic Sound.play. Never steal editor music, paused
portal/horror loops or other pools for a UI cue. Ordinary button attacks may replace an older button tail; a higher-priority
semantic cue can replace a lower-priority semantic tail. No other pool is stolen; deliberately ending the old boot cue on shutdown is lifecycle cleanup.

Selected cues use the existing effects slider/mute, applied to all three UI
pools. They pass through 0.72 router headroom once. Do not multiply both Sound
and channel gains by the same slider. Music remains under its existing separate
controller. There is no new global master control. Respect existing volume
ownership when adding world sounds, especially callers that already pass effects
gain. Ambient/weather/portal/horror buses use 0.60 of their previous gain, with the
existing ambient mute also covering Horror Rain. Selected UI gains rise roughly
4 dB. Horror Rain processes a bounded 30-second view of its preserved rain
recording rather than copying/distorting the entire 12-minute recording.
Keep mix headroom; measure recordings and full audition mixes separately.

World Map retains its MP3 score sequence, plan/completion and quiet rollover
semantics. Ordinary map button activation uses the selected button file. Do not
layer the old click MP3 with it. Cover/reveal uses accepted editor colors and has
a reduced-motion alternative; Escape cancels without editing the saved world.

## World and presentation policy

Classify placement, break, interaction and environment events independently.
Use the existing legitimate material library and source mappings. One actual
mutation produces one material cue; refused/no-op operations do not pretend to
place or break. Use dedicated modern recordings when present and explicit,
documented fallbacks when absent. This pass is not a wholesale block-mechanics audit.

Presentation sound should communicate mass, distance and architecture, not merely
loudness. Close contact has clear attack; distant sources attenuate and narrow.
Reflections have delayed onset and lower energy than the direct path. Pan with
the projected source and camera; keep voices tied to the creature and impacts to
contact locations. The abyss remains sparse and quiet. Preserve the original
piano opening and normal editor soundtrack on exit.

Human-derived distress must remain recognizably recorded voices: distinct breath,
whisper, strain and occasional sharp cries, bounded deep processing, irregular
phrases, pauses and limited overlap. Preserve source attribution and processing
recipes. Do not synthesize substitute vocals. Temporary rig and performance stay
within Pass B; Pass C engineering/UX/consolidation and Pass D original creature remain deferred.

## Listening acceptance and evidence

Pass B uses eleven independently processed recorded vocal sources, two direct
contact recordings and one low-pass reflection recording. The manifest retains
original attribution, source hashes and processing recipes. Channels 37/38 hold
at most two voices, 36 holds one contact, and 39/40 hold at most two reflections.
No scheduler event loops; events more than 250 ms late are dropped, not burst.
The virtual listener uses inverse-distance amplitude with a 42-unit reference
distance (28 for architecture), and camera-relative stereo pan bounded at 0.85.
One scene unit is treated as one metre for the 24/343 and 51/343 second reflected
path delays. These are explicit artistic assumptions, not measured room acoustics.
Direct contacts and skull animation share timeline constants. Existing piano and
editor music remain separately owned. Missing derived recordings fall back to
the preserved earlier score in source checkouts; release packaging rejects them.

Automated checks must decode real recordings, route real SDL channels, exercise
actual save success/failure and mute/ownership, and verify package hashes. Dummy
SDL playback proves scheduling/decoding, not speakers, native physical input or
artistic acceptance. Offline waveform limits do not prove the live mix cannot clip.

Owner listening checklist: boot once; ordinary activation without duplicate cue;
keyboard/mouse close distinct from exit; save/cancel/error correctly distinguished;
map cue with transition and uninterrupted score; mute and low/default effects
levels; clear contacts and source position; quiet sea/abyss between phrases;
human vocal variety and restraint; Skip/exit cleanly release sounds. Repeat with
headphones and ordinary speakers. Record what was actually heard and keep any
unverified device/artistic target open.

See [asset preservation](docs/design/ASSETS.md) and
[reference documentation](docs/design/REFERENCES.md).
