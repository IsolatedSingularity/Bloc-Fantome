# UI audio: ethereal hybrid, with named source material

The target is a small physical event with restrained resonance, not a generic confirmation bleep or a miniature musical fanfare. No sounds were synthesized, generated, cut, or auditioned here. The entries below are named human-authored/designed sources to audition; they are not a falsely “curated” set of unheard WAV filenames.

## Four useful source roles

**Kenney UI Audio:** 50 publisher-listed button/switch/click files, CC0. Use it as a precise dry comparison, not as an automatic aesthetic choice. Too ordinary a click can be rejected even if implementation is convenient. [Source](../SOURCES.md#ui-kenney).

**Kenney Impact Sounds:** 130 publisher-listed foley files, CC0. Audition restrained contacts for the physical component. The archive was not opened, so this kit does not invent specific ceramic, glass or wood member names. [Source](../SOURCES.md#ui-impact).

**pmiller Wind Chimes:** three approximately three-minute loops, CC0; the small Ogg archive is the sensible acquisition route. These are ambient loops, not ready-made UI one-shots. They provide a real resonance source to audition for an infrequent reveal or transition. A future edit should retain the original and record its exact source/time range. [Source](../SOURCES.md#ui-chimes).

**Cinematic Sound Design, Interface & Infographics:** a designed collection of 117 stereo effects at 24-bit/96kHz. Its publisher lists glass, chime, bell, pluck and wood alongside much more technological material, and identifies the synth hardware used. Filter out the alarms, glitch/8-bit cues and overt sci-fi sounds. This is a preview/acquisition reference, not a purchased or bundled pack. [Source](../SOURCES.md#ui-infographics).

## Selection criteria for later audition

For an ordinary action, listen for a clear small onset and a tail that does not accumulate into a wash when the action repeats. For an uncommon completion or scene reveal, a longer resonant decay may be earned. Do not play an elaborate chime on every hover or every block movement merely to make the interface seem polished.

Evaluate a candidate alone, then against the intended piano at working volume. A beautiful standalone ring can obscure a piano phrase. Shortening or attenuating a tail is an editing decision to test, not a reason to generate a replacement sound. Keep a small coherent set of source sounds rather than a different borrowed timbre for every button.

A suggested audition map is: dry restrained transient for selection; slightly resonant acknowledgment for accepted action; softer low-information response for cancellation; a longer airy/resonant event for an infrequent scene reveal. This is a listening brief, not a prescribed sound design or finished event map. Jeff retains artistic selection.

## Files and implementation

[manifest.json](manifest.json) records provenance and whether each source is CC0 or commercial. The selective helper can fetch the three CC0 archives but never extracts or assigns individual sounds automatically. Its receipt includes an archive member inventory after successful retrieval.

Preserve the current audio routing. Trigger a cue on an event edge, not once per render frame or repeatedly while a tutorial gate is waiting. Test burst interactions, muting, scene changes and cancellation. No event-routing change was made in this research pass. [Existing backend](../SOURCES.md#b-audio).
