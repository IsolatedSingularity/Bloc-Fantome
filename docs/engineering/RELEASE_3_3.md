# 3.3.0 release delivery

24 October 2026. The owner accepted atmospheric candidate
`b52fa4b722e7e8dc31a6855c5698178e3dde3ff8` and its documented performance and
memory limitations. This includes the accepted 3.2 source baseline at
`7235d87f336601b73cedcd170019e1505fc427f9`. Publication uses the existing
development and main branches, an annotated v3.3.0 tag and a source-only release.
Version 4 and the Cathedral interface overhaul are cancelled.

## Accepted behavior and verification

Rain has three visual depths, slow wind and intensity changes, exposed top-face
impacts on raised blocks and roofs, and water ripples. Fog uses evolving banks
and the existing painter order. Prepared rain audio retains original recordings,
bounded detail voices and existing channel, volume and lifecycle ownership.
The [atmosphere review](ATMOSPHERE_3_3.md) records the implementation and evidence.

The candidate passed 702 working-tree tests and both deterministic visual checks.
That total includes pre-existing local recovery tests outside the release commit.
Final source and packaged validation are recorded separately in the private
release receipt under `.qa/atmosphere-3.3/release/`.

Trial Chamber cached loading remained near 3 seconds and cold rebuilds near
129 ms. Ocean Monument's full application loop reached a 19.1 ms frame p95.
Whole-process memory grew across scene cycles; stabilization is not established.
Human listening, physical keyboard input, Windows Snap and other checks retain
their stated verification limits. Owner acceptance does not turn these into
passing engineering targets.

## Preservation and delivery gates

The accepted installed 3.1 EXE and root EXE share SHA-256
`72b94c1f66086636e857a96b9c2ab60568e264c9e61acececdb7f3bb163e4dc5`.
The existing 3.1 installer, its input manifest, the accepted 3.2 review EXE and
source rollback remain available. User saves, settings, private source media and
unrelated owner modifications must be preserved throughout the upgrade.

The temporary aggregate QA ceiling is 8 GiB during release preparation. The
owner requires a return below 5 GiB before replacing the root EXE, updating the
installed application or changing the Start Menu shortcut. Cleanup approval must
identify exact existing targets; retain current acceptance evidence and rollback.

The release receipt records source/tag identities, asset checks, packaged archive
contents, installer identity, root and installed hashes, shortcut target/icon/
working directory, actual Start Menu launch, gameplay probes and process cleanup.
A prepared build alone does not establish completed installation.

The independent recovery drive was unavailable at the start of this release.
Existing independent recovery remains unchanged; new local rollback protection
does not establish an updated off-device backup.
