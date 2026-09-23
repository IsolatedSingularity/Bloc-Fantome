# Verification and coverage report

Research date: 20 September 2026. This is a research-kit QA report, not a game-build certificate.

## Completed locally

The 24 bundled helper tests passed using a temporary local HTTP server. They exercised text and ZIP downloads, exact-basename page resolution, redirects, a combined page-to-archive retrieval, transfer limits with/without Content-Length, failed requests, partial-file cleanup, HTML/empty rejection, path containment, archive member validation, no overwriting, no-network dry runs, actual manifest parsing, license inclusion, a lexical scene-method index and pinned tree filtering. See [full test output](qa/helper_tests.txt).

The offline kit validator parses every JSON file, checks Python syntax and Markdown internal links/explicit anchors, verifies the 47-file scene catalogue against fetch targets, checks unique IDs and soundtrack placeholders, and rejects unexpected large/media/font/executable files. See [validation result](qa/validation.json).

Animation-speed, frame-interval, PCM-memory and mask-size examples were calculated in Python. They are dimensional calculations, not observed engine performance. See [arithmetic](qa/arithmetic.json).

The final ZIP was opened and its members CRC-checked after packaging. ZIP member paths are relative and contain one top-level kit folder. No media archives, source downloads, Python caches, executable builds or fonts are included.

## Repository preservation

The initial observed Bloc Fantôme main commit and the final GitHub ref both resolve to `0391259c5ebc0519feb324477fdc1f62bc66ccb7`. Only read/search operations were used against GitHub. No branches, commits, files, release artifacts or issues were created or edited. See [before](qa/baseline_before.json) and [after](qa/baseline_after.json).

There was no local game clone, so this is not described as a clean `git diff` or a local worktree comparison. Work files were created only for this kit in the working container.

## Source coverage

Pinned paths were located through repository reads/searches/directory listings. The source manifest distinguishes code read, representative-method reading, search excerpts, directory entries and a path whose content could not be obtained. Scene-file catalogue completeness is directory-based, not a claim that every storyboard body was deeply analyzed.

The main application file is 1,092,830 bytes; connector attempts returned metadata or a size/unsupported-content error rather than its body. This limited the final render-loop trace. The source helper includes the exact pinned file for later local inspection. Existing regression/visual-test entry points were located, but their game tests were not executed here.

The shader mathematical distinction was checked against actual Voxel Vibes and Pixel Perfect B code, not only a video description. Ponder instruction scheduling/interpolation and the piston/bearing/redstone representative methods were read. Runtime, complete dependency closure and pixel-identical scene playback were not verified.

## External retrieval limitations

The working container could not resolve external hosts. A direct source retrieval reported `Temporary failure in name resolution`; an asset download also failed. Therefore no skybox or sound pack was downloaded into the ZIP, no source-download batch completed live, and no actual external ZIP member list was inspected. The brief permits download scripts instead of bundled assets, and that is the route delivered.

Official pages, repository metadata/source and published download links were inspected through connected/web tools. A verified page or published link is **not** marked as a successfully downloaded payload. Several web binary fetches were unsupported or failed. Page resolvers retain the publisher URL and an exact displayed basename, rather than asserting that a guessed CDN directory exists.

The optional full-Ponder tree discovery logic was fixture-tested, not run against the live API in this environment. The helper checks for truncation and records newly discovered files as not read. PowerShell wrappers were statically reviewed; PowerShell was unavailable, so they were not executed.

## Asset/artistic coverage

Music titles, recording versions and credits were checked against named official/artist/label sources. No audio was played, waveform-analyzed, clipped or loop-edited. Musical fit and UI timbre selections remain audition proposals, clearly labelled in the manifests. No AI music or replacement sound effects were generated.

Qwantani's web preview and Satara's web image were visually inspected. Satara's terrestrial lamps, trees and huts are explicitly noted rather than calling it a pure sky. No panorama was locally decoded, converted to Bloc's atlas format or checked in-engine. Other skies are metadata-based candidates. The current atlas face positions were read; exact per-face flips/orientations across both renderer paths remain a local integration check.

## Resolved factual corrections

The earlier “33 scene groups” figure counted root entries, including folders. The current catalogue has 47 Java scene source files. Ponder's basic movement is linear and Bloc already has 100 ms piston interpolation. `CreateSceneBuilder` is in Create's `foundation/ponder/` package. The inspected piston choreography uses independent sections; no invented `animatePistonHead` helper is included.

Official Xenoblade credits identify A Faint Hope as Yasunori Mitsuda, not ACE. The specific OpenGameArt Space Skyboxes URL belongs to StumpyStrust, not Screaming Brain Studios. Cloudy Skyboxes acquisition uses its presently published filenames and notes its inconsistent prose counts rather than inventing archive contents.
