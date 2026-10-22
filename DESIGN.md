# Bloc Fantôme design specification

Status: owner-approved direction, 2.9.9 Pass B. The Cathedral redesign is reserved
for 3.0. This file separates preservation requirements from future design tokens.
The current owner's request supersedes historical handoffs that still block Pass B.

## Accepted 2.9.9 presentation

Preserve the modern editor at `80df4d745ea3b0b0549bb15893be0247752c45ab`.
The actual source in `Code/ui/chrome.py` and `Code/ui/fonts.py`, and the
[2.9.9 review images](docs/reviews/release-2.9.9/), define this baseline. Earlier
Minecraft-textured chrome/Zekton directions describe legacy surfaces, not a reason
to roll back the accepted modern editor. Do not restyle either during Pass B.

Current modern tokens (RGB): surface 16/24/39, control 30/43/62, hover 47/65/87,
selected 41/61/84, text 230/236/245, muted 153/170/192, accent 173/203/235,
focus 174/208/215, error 245/174/150. Base radius 12, gap 8, margin 24 px.
Panels commonly use alpha 225–246/255. These are implementation facts, not
measurements from the Cathedral concept.

Preserve native Segoe UI selection through the shared font loader, the licensed
Zekton fallback and final-size rasterization. Preserve original pixel-art blocks,
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

The roadmap is Pass B finalization, then Pass C engineering/UX/consolidation,
then Pass D original creature. The official installation and main branch remain
held until owner acceptance after Pass C. This pass changes development only.

The swamp painting presents before bulk assets, with boot audio requested at its
first visible frame. Audio decoding yields to the display/event thread. The
cinematic is manual through Settings > Play Introduction; only an explicit
Autoplay introduction selection enables launch playback. Guided tutorial launch
preferences remain independent. The welcome lesson uses the existing compact
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
confirmation as window close. A second Escape confirms. Stay and Exit are
visible; dirty builds also offer Save and Exit. Pending saves must resolve before
exit, and failure or dialog cancellation retains the world. Shutdown crossfades
to the swamp painting while preserving the selected recording's attack.

Menu retains Save/Open/Settings and groups Editing, Workspace, Explore and
Presentation separately. Four numbered quick-slot rows show occupancy and
separate Save/Load controls, including legacy uncompressed slot files.

## 3.0: Cathedral Soft Blue, Variant D

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
3.0 prototype, not pixel measurements or newly owner-approved styling:

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
