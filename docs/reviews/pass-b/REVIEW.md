# 2.9.9 Pass B finalization review

Development-only finalization is implemented. The current roadmap is **Pass B
finalization, Pass C engineering/UX/consolidation, then Pass D original creature**.
Artistic and physical acceptance remain open. No Pass C work or Cathedral restyle
was started. The official root executable, installed game, Start Menu and `main`
remain unchanged.

Implementation: `39cef8ca`; final native-probe guard and compiled source:
`ddea1e7c`. The following evidence commit changes documentation/artifacts only.
The full suite passed **538 tests in 266.84 s**. See the
[finalization report](finalization/REVIEW.md) and
[machine-readable evidence](finalization/evidence.json) for exact hashes, timing
scope, source/frozen results, failure history and remaining holds.

The boot cue accompanies the first swamp splash. The cinematic defaults to
manual Settings playback. The guided welcome uses the compact sanctuary and the
minimized tile clears the hotbar. World controls have finite state transitions;
Horror Rain now updates, renders and cleans up correctly. Map preparation yields
while real frames present; Library scans and previews avoid repeated blocking
work. Save captures owned state, writes asynchronously and retains edits/revisions.
Escape and window close share a dirty-safe exit dialog and swamp shutdown fade.
Menu keeps Save/Open/Settings and groups four explicit quick-slot Save/Load rows.

- [Welcome before](finalization/welcome-before.png) / [after](finalization/welcome-after.png).
- [Menu before](finalization/menu-before.png) / [after](finalization/menu-after.png),
  [quick slots at 150%](finalization/quick-slots-960-150.png).
- [Tutorial dock before](finalization/tutorial-dock-before.png) /
  [after](finalization/tutorial-dock-after.png), [exit](finalization/exit-960-150.png).
- [Actual presented map frames](finalization/map-presented.mp4).
- [Startup/UI/shutdown with offline reference audio](finalization/startup-ui-shutdown.mp4).
- [Audio balance before](finalization/balance-before.wav) /
  [after](finalization/balance-after.wav).

Native probes use hidden Windows SDL/WGL windows and scripted calls/events. Audio
references are offline mixes of preserved recordings, not microphone/speaker
loopback or human listening approval. Million-block capture still queues editing
input briefly while presenting progress; the existing large-world repaint and
full-cinematic frame-time holds remain open. Device/DPI, listening and artistic
acceptance remain for the owner.

Earlier Pass B evidence and backups remain intact in `.qa/pass-b/` and
[evidence.json](evidence.json). The
[prior review at the starting revision](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/e25a451edcbdd243fb63c52d3f406665f8abf2e8/docs/reviews/pass-b/REVIEW.md)
is historical: its 316–339 ms blocking map activation and 320 ms shutdown tail
are superseded by this finishing pass.
