# Human music shortlist: quiet wonder

Eleven exact recording candidates, not an AI-generated replacement soundtrack. The selection is aimed at a relaxed, melodic opening with meaningful development, without virtuoso busyness or endlessly isolated notes. These are **audition recommendations**: metadata was checked, but no audio was heard or analyzed in this run. Exact BPM, key, loop points and instrument-by-instrument transcriptions are therefore intentionally absent.

## Xenoblade Chronicles 2

**Where We Used To Be**, **Elysium in the Dream**, and **A Faint Hope** are all credited to **Yasunori Mitsuda** in the official list. Their locations are respectively disc 2/04, disc 1/10 and disc 4/17. Earlier conversational attributions of A Faint Hope to ACE were incorrect. [Official credits/acquisition](../SOURCES.md#music-xb2).

My suggested first audition is Where We Used To Be. Compare the other two for space and warmth, but do not infer “solo piano” or the desired emotional fit from a title. Listen through the full arc; a serene opening can lead into a denser or more solemn passage. Learn how much phrase development the scene can support before music becomes the foreground.

## Zelda, in an identified piano recording

Use **Super Piano 64's Zelda & Piano: Ocarina of Time**, not an unspecified fan upload. The publisher identifies solo-piano arrangements with jazz coloration, based on **Koji Kondo's** compositions. Select **Ocarina of Time**, **Zora’s Domain**, **Zelda’s Lullaby**, and **Lon Lon Ranch** from that album. [Recording and listening/store route](../SOURCES.md#music-zelda).

Audition their contrast: lyrical entrance, gentle motion, clear melody, and warmer pastoral character. Those are proposed listening roles, not measured properties of every bar. Check whether embellishment becomes too busy and whether the lullaby remains sufficiently varied. Do not replace a selected version with a similarly named orchestral, lo-fi or automated performance.

## Other game references

**Wet Hands (1:30)**, **Minecraft (4:14)** and **Subwoofer Lullaby (3:28)**, by **C418**, offer three differently sized comparison candidates on Minecraft - Volume Alpha. The artist page provides an actual download-acquisition route. The last is an atmospheric comparison, not a promise of unaccompanied acoustic piano. [Artist release](../SOURCES.md#music-c418).

**Awake**, by **Lena Raine**, from **Celeste Original Soundtrack**, is the outside-series candidate. Test whether its full emotional contour supports this opening; do not import Celeste's narrative associations as a design requirement. [Artist release](../SOURCES.md#music-celeste).

## A useful audition, not an arbitrary playlist

Compare a short opening, a middle phrase and the transition back to silence at similar perceived volume. Ask whether the melody remains clear while reading a prompt; whether the accompaniment develops without demanding attention; whether repeated listening still feels welcoming; and whether a UI resonance clashes with the music's register or harmony. Reject a good composition when this particular recording does not fit the scene.

Human-composed music may use samples or electronic instruments. That is distinct from generated AI music. The identified recordings and artist credits are the provenance anchor; this kit does not certify that every track was a live acoustic two-hand performance.

## Local integration

The [manifest](manifest.json) records exact names, version, credits, official source, fit hypothesis and audition questions. `local_path` and loop points are null until a real local file is supplied and evaluated. Use [the local-file convention](local_music/README.md). Commercial soundtrack audio is not included or automatically fetched, following the approved brief.

Keep Bloc's existing audio backend. It predecodes tracks and can queue ordered fragments. Its MP3-padding trimming is intended for short recovered fragments, so quiet piano tails merit particular testing before reusing that behavior for a new recording. [Existing backend](../SOURCES.md#b-audio).
