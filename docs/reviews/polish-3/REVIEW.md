# 3.0 polish candidate: HOLD

Historical evidence. Local-only artifacts are recorded as paths; see the [recovery index](../../QA_ARCHIVE.md). Acceptance statements below describe that review date, not the current release.

Historical review status. On 22 October 2026 the owner accepted this candidate and its documented performance limits for release. The final validation and installation record is [Bloc Fantôme 3.0.0](../../releases/3.0.0.md); the original findings below are preserved.

The requested visual and interaction corrections are ready for owner review. This is not a release approval: large-world frame stalls remain, and physical keyboard/Snap coverage is incomplete.

Development baseline: `8abcf8e1006fc1fe5bdd7275a9ce9e96d53eff1b`. The verified local rollback bundle is `.qa/polish-3/rollback.bundle`, with a source archive alongside it. Main remains at `2ea56e3438263aae0a8ec4fc9879e49f341d9660`. Root/installed executables, shortcuts, README and owner `night.png` were excluded.

## Changes and visual evidence

World actions now retain the drawer, including terrain operations and repeated World navigation. Explicit X/Escape dismissal and nested cancellation remain covered. Clouds have separate layered paths; snow uses readable individual flakes; sunlight rotates, the lunar state reveals stars, and the active Nether control moves. Reduced Motion remains static. Major shells are square, with rounded internal controls; Exit is smaller and more translucent. Navy, Plex, small HUD controls and Goodbye remain intact.

Compare the seven production panels: [Library](comparison/library.png), [World](comparison/world.png), [Tools](comparison/tools.png), [Build](comparison/build.png), [Menu](comparison/menu.png), [Settings](comparison/settings.png), [Exit](comparison/exit.png). [Rendered motion states](motion-states.jpg) supplement the native World recording (local artifact: `world.mp4`), startup (local artifact: `startup.mp4`) and Goodbye (local artifact: `goodbye.mp4`).

Dimension framing is individually tuned: tighter villages, modest Nether/Ocean changes, full Ancient City landmarks, unchanged End composition. The bell is exclusive to Biomes' Overworld rail. All 37 curated biome source identities and thumbnails were audited, opened and compared to their exact source cell positions ([opened gallery](opened-biomes.jpg), [checks](all-opened-scenes.json)). Swamp previously showed a village-dominated capture; its derived 32×32 view retains original cells and palette, with 58.6% Swamp among biome-tagged columns and natural river/plains edges. Small End Islands retains three complete separated islands. Canonical captures and tutorial scenes are unchanged. See [gallery](biomes-audit.jpg), [dimensions](dimensions-audit.jpg), [source audit](biome-audit.json), [Swamp opened](swamp-opened.png), [islands opened](islands-opened.png), and derived provenance in `Code/biome_captures/derived/manifest.json`.

## Audio and verification

World/Tools button and toggle variants are shorter and quieter; originals and unrelated cues retain their hashes. Audition (local artifact: `interaction-audition.wav`) order: old button, new button, old toggle, new toggle. Ordinary natural music transitions use a one-third piano lottery with 2:2:1 chapter weights. A seeded 12,000-transition check selected piano 33.1%, without immediate repeats. Intro autoplay, cinematic sequences and reserved channels remain unchanged.

Full chapters decode asynchronously, with a bounded cache. Review caught and fixed eviction of an already prepared next track. [Actual chapter decoding](chapter-decoding.json) retained full 258/215/200-second durations; prepared transitions took under 0.06 ms. Initial worker setup had a 49 ms outlier. [Startup continuity](audio-continuity.json) found no unexpected silent intervals in source/frozen loopback recordings; this is signal analysis, not listening approval.

The full suite passed **631 tests** before the final cache correction; **63** [focused final tests](focused-tests.txt) cover audio, World actions and finishing behavior afterward. Source/frozen integration covers saving, failure/cancellation, World Map, manual Introduction and worker shutdown. Native QA checks nine size/text-scale combinations and fullscreen restoration. [Physical checks](physical-checks.json) verify source/frozen mouse input plus packaged resize and minimize/restore. Helper-generated Escape produced no visible response, so physical keyboard coverage remains inconclusive despite passing SDL event tests. Snap, precision trackpad, other OS DPI settings and multiple monitors remain unverified; title dragging was attempted without a measured displacement.

## Remaining limits and handoff

[Matched rendering](performance/summary.json) preserved exact pixels in all sampled operations. Ocean Monument pan medians were 345 ms baseline / 378 ms candidate; edit medians 118 / 122 ms. Trial Chamber pans reached 759 ms. Four measured runs and overlapping QA do not establish a timing regression, but the stalls remain unacceptable for a release PASS. [Startup comparison](startup-timing.json), three runs each, was comparable at 12.80 / 12.73 seconds before the final cache-only correction.

The local review build is `.qa/polish-3/package/BlocFantome.exe`; [package identity](package.json) records its hash and asset checks. Its adjacent Assets junction uses this checkout's owner-supplied assets, so the EXE alone is not portable. Owner visual/listening acceptance and unresolved QA gates remain pending. Do not promote or install this candidate as the accepted release.
