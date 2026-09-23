# Complete scene-file catalogue at the pinned Create snapshot

The inspected directory tree contains **30 root Java files + 6 fluid + 6 high-logistics + 5 train files = 47 Java scene source files**. An earlier count of 33 described the root's 30 files and three subdirectories, not 33 scene families. One source file can program multiple storyboards; this is not a count of registered tutorials. The template is counted as a file and identified separately.

All entries have pinned paths in [scene_catalog.json](scene_catalog.json) and [the source manifest](../scripts/source_manifest.json). Coverage is explicit: three representative files received method-level analysis; the other entries were located, not exhaustively audited. Subject labels below are navigational descriptions based on file names and available context, not claims about uninspected method bodies.

| File | Folder | Navigation subject | Coverage |
|---|---|---|---|
| `ArmScenes.java` | root | Mechanical-arm presentation | Entry only |
| `BearingScenes.java` | root | Bearing-driven rotation and windmill assembly | Representative methods read |
| `BeltScenes.java` | root | Belts and transported items | Entry only |
| `CartAssemblerScenes.java` | root | Minecart-mounted assemblies | Entry only |
| `ChainDriveScenes.java` | root | Linked drives | Entry only |
| `ChassisScenes.java` | root | Assembly membership and attachment | Entry only |
| `ChuteScenes.java` | root | Vertical item transfer | Entry only |
| `CrafterScenes.java` | root | Mechanical crafting | Entry only |
| `DeployerScenes.java` | root | Deployer actions | Entry only |
| `DetectorScenes.java` | root | Detection behavior | Entry only |
| `DisplayScenes.java` | root | Display presentation | Entry only |
| `EjectorScenes.java` | root | Ejection | Entry only |
| `ElevatorScenes.java` | root | Elevator presentation | Entry only |
| `FanScenes.java` | root | Fan direction and airflow | Entry only |
| `FunnelScenes.java` | root | Funnel transfer | Entry only |
| `GantryScenes.java` | root | Guided mechanical translation | Entry only |
| `ItemVaultScenes.java` | root | Item storage | Entry only |
| `KineticsScenes.java` | root | Rotational-power fundamentals | Entry only |
| `MechanicalDrillScenes.java` | root | Drilling | Entry only |
| `MechanicalSawScenes.java` | root | Sawing | Entry only |
| `MovementActorScenes.java` | root | Moving assembly actors | Entry only |
| `PistonScenes.java` | root | Mechanical piston translation and extension poles | Representative methods read |
| `ProcessingScenes.java` | root | Processing sequences | Entry only |
| `PulleyScenes.java` | root | Vertical movement | Entry only |
| `RedstoneScenes.java` | root | Sticker, contacts and signal explanations | Representative methods read |
| `RedstoneScenes2.java` | root | Additional redstone explanations | Entry only |
| `RollerScenes.java` | root | Roller behavior | Entry only |
| `SteamScenes.java` | root | Steam mechanisms | Entry only |
| `TemplateScenes.java` | root | Authoring template, not a feature count | Entry only |
| `TunnelScenes.java` | root | Belt-tunnel routing | Entry only |
| `DrainScenes.java` | fluid | Drains | Entry only |
| `FluidManipulationScenes.java` | fluid | Fluid operations | Entry only |
| `FluidTankScenes.java` | fluid | Tanks | Entry only |
| `PipeScenes.java` | fluid | Pipe presentation | Entry only |
| `PumpScenes.java` | fluid | Pumps | Entry only |
| `SpoutScenes.java` | fluid | Fluid application | Entry only |
| `FactoryGaugeScenes.java` | highLogistics | Factory gauges | Entry only |
| `PackagerScenes.java` | highLogistics | Packaging | Entry only |
| `RepackagerScenes.java` | highLogistics | Repackaging | Entry only |
| `StockLinkScenes.java` | highLogistics | Stock links | Entry only |
| `StockTickerScenes.java` | highLogistics | Stock ordering | Entry only |
| `TableClothScenes.java` | highLogistics | Table-cloth logistics | Entry only |
| `TrackObserverScenes.java` | trains | Track observation | Entry only |
| `TrackScenes.java` | trains | Track construction | Entry only |
| `TrainScenes.java` | trains | Train fundamentals | Entry only |
| `TrainSignalScenes.java` | trains | Rail signals | Entry only |
| `TrainStationScenes.java` | trains | Stations | Entry only |

## Recommended entry points

Start with `PistonScenes.movement`, `PistonScenes.poles`, `BearingScenes.windmillsAsSource`, `RedstoneScenes.sticker` and `RedstoneScenes.contact`. These were directly inspected. Their teaching mechanisms are discussed in [the deep dive](piston_redstone_deep_dive.md).

Belts, gantries, pulleys and train assembly are useful next-reading candidates for a future agent, not examples declared visually superior without inspection. Fetch them selectively or fetch the whole small scene-code set. The included method indexer discovers candidate storyboard methods after downloading; it does not parse Java control flow or infer exact registry bindings.

The authoritative item-to-scene registration remains `AllCreatePonderScenes.java`. To establish exact playable coverage, evaluate its registrations and conditional dependencies rather than equating source-file count with user-visible scenes. [Registry](../SOURCES.md#c-registry).
