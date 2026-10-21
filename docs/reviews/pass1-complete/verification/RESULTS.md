# Verification index

Source commit: `98fc6485fc6575c0bbd0210722836592859f4d8a`, descended from the approved `f63db3ab` review. [Changed source hashes plus prepared bundle manifest](source-manifest.json). Windows Python 3.12.10, Pygame 2.6.1 / SDL 2.28.4. Original engineering ownership, stale-job, atomic-write and exact visibility contracts remain in the full suite.

| Layer | Result | Evidence |
|---|---|---|
| SOURCE/TEST | **464 passed, 198.60 s** | [Complete suite XML](release-suite.xml) |
| Python fallback | **45 passed, 15.95 s**, native accelerator disabled | [Fallback XML](fallback.xml) |
| Focused UI/opening | **40 passed** | [Focused XML](polish.xml) |
| Corrupt loads/settings/tutorial recovery | **26 passed** | [Recovery log](recovery.log) |
| Prepared lesson cache | All 12 large lesson records regenerated; fail-closed validation retained | [Bake log](bake-release.log), full suite |
| NATIVE UI | Windows 125% DPI; three sizes; 100/125/150% in-app text; fullscreen and save/reopen assertions | [Matrix](../native/matrix-iteration2.json), [final checks](../native/final-checks.json) |
| AUDIO | Real SDL mixer routing tests; finite unclipped derived audition signals; subjective acceptance pending | [Analysis](../audio/analysis.json), [mix provenance](../audio/mix-provenance.json), [derived runtime hashes](derived-audio.json) |
| PERFORMANCE | Small-editor UI p95 target met; inherited large-load/camera holds remain; opening not 60 FPS | [Editor](../performance/editor1080.json), [opening](../performance/opening1080.json), [UI loop](../performance/ui-latency.json) |
| PACKAGED | Final isolated EXE compiled and visibly launched into native opening | [Build log](build-final.log), [package hash](package.json), [opening screenshot](../native/packaged-opening.png) |
| INSTALLED | Intentionally unchanged; no shortcut/installer/main promotion | [56-target before/after hashes](preservation.json) |

The packaged archive contains `ui.feedback`, `ui.history`, `ui.opening_piano`, `ui.workshop_actions`, the Rust accelerator and all prepared tutorial records. Raw archive listing remains local at `.qa/pass1-complete/package-archive-final.txt`. The review EXE uses the workspace Assets junction, which includes the ten new derived audio files; it is not a portable installer. Final QA processes were closed and the exact executable path was checked for zero remaining processes.

Earlier full validation recorded [453 passes and 10 failures](final-suite2.xml): four obsolete UI-layout assertions and six corrupt-load tests exposing a missing optional-UI guard. The controls tests now use displayed geometry; the load error handler tolerates a headless/partially initialized app and preserves the live world. The complete final rerun passes. Initial silent-output runs were interrupted for diagnosis; they are not counted as passing runs.

Native limitations: OS keyboard injection did not reach the source app and did not visibly exit the packaged opening; later source automation also encountered stale window bindings. Mouse evidence and scripted handler tests are labeled separately. Windows 100/150/200% display scaling, monitor transfer, minimize/focus recovery and the complete uninterrupted native editing/import/save workflow are not accepted by inference. Windows Settings was inspected only; scale remained 125%.

Reproduce from the checkout with its existing private assets and `.venv`:

```powershell
.venv/Scripts/python.exe Code/tools/bake_tutorial.py
.venv/Scripts/python.exe -m pytest -vv --basetemp=.qa/review-tests
$env:BLOC_FANTOME_DISABLE_NATIVE='1'
.venv/Scripts/python.exe -m pytest tests/test_build_io.py tests/test_public_contract.py tests/test_input_commands.py tests/test_opening_audio.py tests/test_workshop_production.py -q --basetemp=.qa/review-fallback
Remove-Item Env:BLOC_FANTOME_DISABLE_NATIVE
.venv/Scripts/python.exe Code/build_exe.py --output-dir .qa/review-package
```

Do not run the builder without the isolated output argument for this unaccepted review. [Archived QA scripts](../reproduction/NOTES.md) retain the original paths and assumptions. Installed/root executables are outside this handoff's promotion scope.
