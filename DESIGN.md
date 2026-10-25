# Bloc Fantôme design specification

Status: 3.3.0 was owner-accepted on 24 October 2026, including its documented
performance and memory limits. It retains the accepted workshop and adds layered
rain, elevated surface impacts and slowly moving depth-aware fog. The existing
World controls, Reduced Motion, dimension rules and Horror Rain remain authoritative.
See the [atmosphere review](docs/engineering/ATMOSPHERE_3_3.md) and
[current roadmap](docs/ROADMAP.md). Version 4 and the Cathedral redesign are
cancelled. Dated Pass A/B/C statements below describe design history.

## Accepted 2.9.9 presentation

Preserve the modern editor at `80df4d745ea3b0b0549bb15893be0247752c45ab`.
The actual source in `Code/ui/chrome.py` and `Code/ui/fonts.py`, and the
[2.9.9 review images](docs/reviews/release-2.9.9/), define this baseline. Earlier
Minecraft-textured chrome/Zekton directions describe legacy surfaces, not a reason
to roll back the accepted modern editor. Do not restyle either during Pass B.

Current modern tokens (RGB): surface 16/24/39, control 30/43/62, hover 47/65/87,
selected 41/61/84, text 230/236/245, muted 153/170/192, accent 173/203/235,
focus 174/208/215, error 245/174/150. Base radius 12, gap 8, margin 24 px.
Modern satin panels generally use alpha 232–246/255 (225 for lighter HUD overlays), with a subtle
continuous antialiased edge. Text and controls remain opaque. These are implementation facts, not
measurements from the Cathedral concept.

Use bundled IBM Plex Sans Regular for functional text and selectively Light for headings
through the shared font loader. Preserve branding, licensed Zekton/system fallbacks
and final-size rasterization. Preserve original pixel-art blocks,
thumbnail previews, generated navigation artwork, responsive Build category rail,
Library home/gallery transformation and explicit Open/Place, compact Menu and
World controls, draggable tutorial, hotkeys, and four-second HUD inactivity fade.
Reduced motion removes decorative animation; invisible controls must not capture
input. At 960x640 and enlarged text, reflow content rather than scaling cached text.
The small World Map transition and persistent introduction Skip are authorized
Pass B additions. They must use existing chrome, not Cathedral styling.

Pass A's direction is owner-accepted. Performance and incomplete native keyboard,
trackpad and OS DPI checks remain distinct holds; acceptance of style is not a
claim that those checks passed.

## Pass B finalization contracts

Historical context: Pass B was provisionally accepted on 22 October 2026.
The later 3.0 release superseded its candidate status and upgraded the installed
application. The following behavior contracts remain in force for 3.1; the
original creature and optional encounter remain unchanged.

The swamp painting presents before bulk assets, with boot audio requested at its
first visible frame, with its cue decoded before presentation. Three small original
geometric blocks jump left, middle, right during actual loading. Each rises, hangs,
lands and settles before the next starts; no delay is added. Reduced Motion holds them still. Audio decoding
yields to the display/event thread. The
cinematic is manual through Settings > Play Introduction; only an explicit
Autoplay introduction selection enables launch playback. The guided tutorial opens
only deliberately, including when an old saved preference requested auto-launch.
Its quiet book dock remains available; the panel states that it opens manually.
The welcome lesson uses the existing compact
sanctuary, closely framed with sky and lighting. Its minimized tile sits 8 px
right of the selected-block preview, lifting above it when the hotbar needs room.

World controls retain their approved artwork, add a finite 200 ms state switch
and explicit On/Off text, and snap immediately under Reduced Motion. Fresh
skybox settings follow asset availability; saved choices remain authoritative.
Horror Rain is exclusive with ordinary precipitation, cleans its loop on exit or
dimension change, and uses a cached haze rather than world-size per-frame fog work.

The map unfolds from its central fold over fixed contour artwork, then reveals
the actual map outward. Independent preparation includes data, atlas composition
and music decoding. Worker blits yield between bounded batches. Cancellation
never commits a partial map. At most two prepared viewports remain cached.
Library Structures avoids scanning saves; Saved Builds scans asynchronously;
world/biome preview sources are retained within the existing byte budget.

Save presents Saving… before an independently owned snapshot is captured. A
single worker handles serialization/compression/atomic writes and autosave
backups. Capture interns immutable property values and pumps/presents progress
in bounded batches while input remains queued; mutation dispatch resumes when
capture finishes. The writer streams v5 records without another world-sized list.
Success belongs to the captured revision and document, including edits
made during writing. Background saves never mark a manual document clean.
Escape first belongs to existing modals/tools; otherwise it opens the same exit
confirmation as window close. Stay has initial focus; Escape returns to the game.
Only explicit Exit confirms departure. Stay and Exit are
visible; dirty builds also offer Save and Exit. Pending saves must resolve before
exit, and failure or dialog cancellation retains the world. Shutdown uses a
full-bleed nighttime Goodbye screen for 3 seconds, with a 350 ms audio fade.
The original root `night.png` (PNG, 2560×1419) is preserved byte-for-byte in
`Code/ui/art/goodbye-night.png`. Focal-point cover protects the moon and two figures.
Eight quiet farewell messages accompany restrained text arrival and the same
three boot blocks, jumping right, middle, left with softer motion settling before the fade;
Reduced Motion is static. Any key, click or window close skips it immediately;
already-running SDL jobs still finish safely before SDL teardown. The boot overlay
cannot enter exit confirmation, and no editor frame renders after confirmed Exit.

Menu is a compact floating command palette: Save/Open/Settings, then File, Edit,
View and More. File expands four quick slots with occupancy and separate
Save/Load controls, including legacy files. Arrow keys change groups/focus;
Tab, Enter, scrolling and existing shortcuts remain available.

Only Library Dimensions uses the generated flat white village and End-island
variations, matching the existing monochrome artwork and sampled from their
original masks at native display size. Procedural isometric art is not used. World dimension icons and
the Nether artwork retain their accepted forms. Fresh Overworld terrain remains
grass; skyboxes default on when assets are available, with saved settings
respected. Lighting
shows changing face illumination and a grounded shadow; cloud layers drift
independently. Other existing feature animations retain their visual roles.
Small frame caches replace repeated image transforms; disabled tiles and Reduced
Motion remain static with truthful On/Off state. The map's fixed cover/reveal
timing and score are unchanged; its intermediate panel adds a small compass,
unlabelled scale ticks and survey points without additional preparation work.

Normal editor chrome has no version label; The window title retains
the version. Settings has no visible version footer. VSync is visibly unavailable: this native software RESIZABLE display
uses neither OPENGL nor SCALED. Pygame only accepts a VSync request for those
modes and does not guarantee it. No ineffective preference or renderer migration
is introduced. Pass C may evaluate a renderer change with resize, DPI, coordinate
and physical refresh verification. See the
[Pygame display contract](https://www.pygame.org/docs/ref/display.html#pygame.display.set_mode).

Enlarged opaque editor cubes reproject their original face textures at the final
sprite dimensions above 1× zoom. Texture sampling remains nearest texel; only
the exterior silhouette uses coverage antialiasing, with one-output-pixel edges.
Normal and overview views, transparent/modelled blocks and captured Java atlases
retain the existing pipeline. Fullscreen remains a native desktop surface, with
no low-resolution viewport enlargement. Original 16×16 texture detail is preserved.

## 3.0: Pass C consolidation

Preserve accepted Pass B. Restore the small book with a persisted white unread dot;
center and enlarge Goodbye; pair atlas opening and closing; profile startup and
large-world repaint work. IBM Plex is an opt-in visual experiment only. Segoe UI
remains the default pending owner review. The original creature replacement stays
separate. Only local main was fast-forwarded to the accepted 2.9.9 source; 3.0
remains unpromoted and the working installation is preserved.

## 4.0: Cathedral Soft Blue, Variant D

Primary target: [unchanged owner PNG](docs/design/references/cathedral-soft-blue-variant-d.png).
SHA-256: `62a34de6bd3b7aaf9ef9be9d07450c043d0b884264a6b33cb52339e71d72df51`.
The original Downloads path was missing; this existing repository copy was
available and visually inspected. Preserve its bytes, including the lower guide.

Architectural, quiet, spacious, graceful and slightly mysterious. Deep navy and
charcoal carry pale blue light and restrained ivory typography. Avoid technological
HUD decoration. The cathedral setting conveys atmosphere; it does not authorize
replacement of Minecraft worlds. People and Multiplayer in the concept are not
approved game systems. The bottom palette/type/motion/audio strip is documentation,
never an in-game toolbar. Variant A's narrow left icon rail and Variant E's optional
toolbar labels are approved directions; their separate source images are pending.

### Palette

The six printed swatch labels in the reference are the canonical design colors.
Rendered swatches include lighting/gradients, so sampling their centers can differ.
For reproducibility, median RGB samples from the original 1491x1055 image at
y=878–903 per mille and x=38/76/115/154/192/230 per mille (14 per mille wide)
were respectively 12/22/35, 32/46/66, 193/204/220, 140/179/235, 192/221/252,
243/211/169. These sampled colors are evidence, not replacements for printed tokens.
Keep semantic tokens separate from sampled pixels. Warm Light is a rare warm
material/attention accent, not the body-text color.

| Token | Label | Hex | Intended use |
| --- | --- | --- | --- |
| cathedral.navy | Cathedral Navy | `#0B1320` | Deep background |
| cathedral.charcoal | Charcoal | `#1A2433` | Elevated chrome |
| cathedral.masonry | Masonry | `#C9D3DF` | Quiet text and icon base |
| cathedral.blue | Soft Blue | `#8FB6E6` | Active/focus highlight |
| cathedral.glass | Glass Blue | `#B7D7F7` | Sparse brighter highlight |
| cathedral.warm | Warm Light | `#F2D7A7` | Restrained warm accent |

Use ivory/white text only where needed for hierarchy. Test actual composited
backgrounds, including bright terrain, rather than assuming these pairs pass.

### Layout, type and icon language

The reference shows a narrow left navigation rail, a dominant central canvas,
and compact right-side content panels. Layout must adapt to available space.
Hide optional toolbar labels as a group when space is tight, then recenter the
remaining icons in their available group. Preserve accessible names/tooltips and
keyboard focus. Do not shrink labels into illegibility. Do not turn galleries
into text lists or remove content previews. Rail width is not specified in pixels
by the concept; determine it with real labels and target-size screenshot reviews.

Functional chrome uses installed Segoe UI regular/semibold. Use the existing
licensed fallback when unavailable; never bundle Microsoft's system font files.
The elegant serif Bloc Fantôme wordmark is an intentional branding exception.
Its exact font identity is unconfirmed; do not guess or substitute it silently.
The guide specifies size/line-height pairs: display 32/40, title 24/32, header
18/24, body 14/20, caption 12/16. These are future logical-pixel tokens, not a
request to shrink existing readable 2.9.9 text.

Original monochrome geometric outline icons, consistent optical weight, rounded
forms and sparse fill. Render from geometry at final native resolution and cache
by actual size/DPI. Keep crisp pixel interpolation for Minecraft assets separate
from antialiased icon/chrome rendering. No scaled low-resolution text surfaces.

### Interaction and implementation proposals

The following numeric values are provisional engineering defaults for a future
4.0 prototype, not pixel measurements or newly owner-approved styling:

| Property | Proposed starting point | Review criterion |
| --- | --- | --- |
| Spacing | 4, 8, 12, 16, 24, 32 logical px | Optical alignment, compact groups, clear breathing room |
| Radius | 6 controls, 12 panels | Consistent curves without bubbly appearance |
| Surface opacity | 88–96% | Fine layering, readable over bright/dark worlds |
| Outline | 1 logical px | Consistent pale-blue edge, not glowing borders |
| Hover | 120 ms, small luminance/elevation change | Quiet, no layout jump |
| Press | Immediate darken/inset | Activation on deliberate input |
| Focus | Continuous visible ring | Distinct from hover and selection |
| Disabled | Muted, unchanged geometry, no activation cue | Still understandable |
| Panel motion | 200–300 ms, eased | Reference range; interruptible and reciprocal |
| Reduced motion | Immediate state or brief opacity only | Same controls and outcome |

Layer order: world, world selection/placement, navigation, drawers, modal dialogs,
tooltips/critical messages. Clip both visuals and input to animated bounds. Never
make users wait for decorative animation before a cancel/skip command works.
Use contextual movement to communicate relationships; no uniform idle oscillation.
Keep atmospheric scale and negative space without hiding essential controls.

Accessibility targets: normal text contrast at least 4.5:1, large text 3:1;
visible focus and non-color state cues; keyboard activation/back/cancel; mute and
reduced motion; readable layouts at 100/125/150% text and 960x640 through FHD.
These targets do not assert formal WCAG conformance for this Pygame application.
Record OS DPI actually tested separately from in-app text scale.

Future screenshot comparison must compare rail/canvas/panel proportions, hierarchy,
palette relationships, outline weight, spacing, translucent readability and pixel
fidelity at matched viewports. It must not compare the whole concept sheet against
a game screenshot as if the documentation strip or concept scenery were runtime UI.

See [review checklist](docs/design/REVIEW_CHECKLIST.md),
[references](docs/design/REFERENCES.md), [asset register](docs/design/ASSETS.md),
and [audio specification](AUDIO_DESIGN.md).

## Final 3.0 finishing contracts

The accepted drawer organization and navy identity remain intact. A single floating
window fits the complete swamp painting and remains the editor window. Its final
loading frame fades directly into the complete editor. The unchanged boot recording
hands off to the menu bed; compressed OGG/MP3 decoding uses libsndfile outside
SDL_mixer's playback lock. WAV cues, channel ownership and the 1024-sample buffer
remain unchanged. Three cubes are 18% larger at unchanged centers, with ballistic
descent, finite contact compression and damped recoil. Reduced Motion is static.

Windows uses a 28px navy title with SDL native hit testing for drag/edge resize.
Minimize, desktop fullscreen/exact floating restore and Close share real input
routes. F10 focuses title controls; arrows/Tab, Enter/Space and Escape operate them.
Unsupported drivers or BLOC_NATIVE_FRAME=1 retain the native frame. Map controls
clear the title region; the opening GPU overlay uses the same strip.

World toggles use translucent colored material, white original masks and individual
rain, snow, celestial, cloud, illumination, sky, horror and current motion. Their
short transitions preserve truthful On/Off states; static actions do not loop.
The End action uses a simpler original island/pillar silhouette. Settings is a
measured floating inspector with three inline audio sliders/mutes, preference
switches, a separate Play Introduction action and quiet unavailable VSync text.
Autoplay stays off by default. Keyboard and mouse use the same control rectangles.

Selection and preference changes have separate non-destructive piano derivatives;
the accepted owner recordings retain their hashes. The Pass C renderer is retained:
the bounded follow-up experiment did not earn inclusion. Review evidence and the
remaining physical/artistic checks are in docs/reviews/final-3/REVIEW.md.
Stage A preserves root and installed executables. Stage B promotion, root build,
installation and Start Menu delivery require explicit owner acceptance.
