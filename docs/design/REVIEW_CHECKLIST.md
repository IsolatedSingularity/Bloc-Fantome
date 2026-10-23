# Design review checklist

- Name the version and baseline. Keep 2.9.9 preservation separate from 4.0 proposals.
- Inspect actual rendered captures at 960x640, 1200x800 and 1920x1080, with
  100/125/150% text. Record actual OS DPI and display backend; do not infer them.
- Compare bright/dark terrain, menus, Build, Library home/gallery/back, World,
  Settings and tutorial. Check clipping, measured labels, focus and hidden hitboxes.
- Preserve generated owner-selected art and original pixel-textured world assets.
- Review transitions in motion, including rapid reversal, resize and reduced motion.
- Test deliberate activation, successful save, cancellation, real error, mouse and
  keyboard close, World Map open, boot and shutdown. One semantic cue per action.
- Hear the selected sounds at low and default levels, muted/unmuted, with music,
  on headphones and ordinary speakers. Automated channel checks do not approve art.
- Skip shrine, approach, sanctuary and encounter by mouse and Escape. Verify editor
  world, camera, undo and save path; no lingering opening audio or graphics resources.
- Review sea motion and creature contacts in multiple views over time. Reject
  noisy flicker, cyclic floating, generic synthesized vocals and excessive reverb.
- Measure camera stalls, frame tails and memory under documented conditions.
  Keep unresolved gates explicit; do not hide them behind passing test counts.
- Verify original asset hashes, backup extraction, source/frozen lookup and required
  package media. Keep the installed version untouched until owner acceptance.
