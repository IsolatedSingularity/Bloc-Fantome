# Actionable engineering register

23 October 2026. Reproductions and existing fixes take precedence over historical
audit suggestions. The current scope is [the roadmap](../ROADMAP.md).

| Priority | Unresolved work | Evidence and completion criterion |
| --- | --- | --- |
| P1, 3.2 | [Large-world camera/edit/load latency, issue #1](https://github.com/IsolatedSingularity/Bloc-Fantome/issues/1) | Accepted 3.0 profiles and 3.1 large-world traces exceed existing targets. Measure complete input-to-visible updates, preserve pixels/order/save state, and meet or explicitly retain failing targets. Follow the staged architecture/performance plan. Published with explicit owner approval; implementation remains deferred. |
| P1, preservation | Verify independent recovery of private/irreplaceable inputs | Same-device archives restored successfully; no independent device/remote restore was verified. Copy exact media, worlds, references, saves/settings and rollback, compare hashes and test restoration. |
| P1, historical publication | Decide whether previously public raw media/personal QA objects need historical remediation | Current-tree removals retain all originals but do not retract old Git objects. Privately classify the affected history and decide a separate remediation scope; do not rewrite tags/history automatically. |
| P2, acceptance | Finish physical keyboard, Snap, trackpad/multi-monitor/other OS DPI and human listening | Native mouse and injected SDL events pass. Helper-generated Escape had no visible effect, so keyboard remains inconclusive. Snap is unverified with available input capabilities. Review loopback audio by listening. |

Fixed in 3.1: Java indexed sound extraction/path loss/unsafe overwrite behavior,
unverified stale native reuse, shared save/cache staging names, missing world-cache
payload integrity, fresh-clone pytest temporary-parent setup, and benchmark writes
to source preferences, plus integration-test user-data isolation. These do not need
duplicate open issues. Earlier undo, asynchronous stale-result ownership, atomic
preferences and prepared-cache fixes remain present and are revalidated.

The research branch is retained for unique evidence, not classified as a defect.
Architecture extraction is planned work; line count alone is not an issue.
