# Design references

| Reference | Authority / use |
| --- | --- |
| [Cathedral Soft Blue Variant D](references/cathedral-soft-blue-variant-d.png) | Owner primary visual target for 3.0; unchanged PNG |
| [2.9.9 checkpoint](../reviews/release-2.9.9/REVIEW.md) | Accepted visual/functional baseline; performance/native limitations remain |
| [Owner roadmap](../handoffs/OWNER_ROADMAP_AFTER_PASS_A_2026-10-21.md) | Pass B intent; latest direct request unlocks B, C remains paused |
| [Pygame mixer](https://www.pygame.org/docs/ref/mixer.html) | Channel reservation, nonblocking playback, channel vs Sound gain; runtime pinned 2.6.1 |
| [OpenAL programming guide](https://www.openal.org/documentation/OpenAL_Programmers_Guide.pdf) | Distance attenuation model reference; Pygame implementation uses a virtual orthographic listener, not OpenAL |
| [FFmpeg rubberband filter](https://ffmpeg.org/ffmpeg-filters.html#rubberband) | Recorded-source pitch, tempo and formant processing; exact filters/version/hashes in pass-b-derived-audio.json |
| [Inno Setup FileExists](https://jrsoftware.org/ishelp/topic_fileexists.htm) | Required-media installer compilation checks |
| [Fluent motion](https://fluent2.microsoft.design/motion) | Functional transitions and relationship-preserving movement; principles only, no web dependencies |
| [W3C contrast explanation](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | Readability targets, checked against composite backgrounds |

External documentation retrieved during Pass B. No Impeccable/Taste framework
installed or claimed as reviewed. Variant A/E separate images remain unavailable;
their rail/optional-label requirements are supplied in the owner's request.
The concept's sound strip is aesthetic guidance. The seven selected WAVs are
authoritative for 2.9.9. No concept image implies new multiplayer functionality.

## Pass B finalization runtime references (2026-10-22)

The implementation targets the checkout's Python 3.12.10, Pygame 2.6.1 and
SDL 2.28.4. [Pygame events](https://www.pygame.org/docs/ref/event.html) and
[display ownership](https://www.pygame.org/docs/ref/display.html) support keeping
pumping/presentation on the display thread while independent preparation runs
on workers. [Python 3.12 futures](https://docs.python.org/3.12/library/concurrent.futures.html)
inform cancellation and shutdown: cancellation cannot stop work already running,
so canceled map preparations remain tracked until their SDL work finishes.
