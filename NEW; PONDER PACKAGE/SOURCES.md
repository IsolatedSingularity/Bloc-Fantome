# Sources and scope

Primary sources inspected on 20 September 2026. Code links are pinned. Page metadata and download availability may change. A source entry proves only the coverage described, not that the code was built or an asset was auditioned.

<a id="p-license"></a>
## p-license
[LICENSE](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/LICENSE)
MIT, copyright The Create Team.

<a id="p-scene"></a>
## p-scene
[common/src/main/java/net/createmod/ponder/foundation/PonderScene.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/PonderScene.java)
Schedule, virtual world, reset/replay, render passes and SceneTransform.

<a id="p-builder"></a>
## p-builder
[common/src/main/java/net/createmod/ponder/foundation/PonderSceneBuilder.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/PonderSceneBuilder.java)
Scene facade, explicit delay instructions, 20 ticks per second convention.

<a id="p-api"></a>
## p-api
[common/src/main/java/net/createmod/ponder/api/scene/SceneBuilder.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/api/scene/SceneBuilder.java)
Documented storyboard API and delay semantics.

<a id="p-story"></a>
## p-story
[common/src/main/java/net/createmod/ponder/api/scene/PonderStoryBoard.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/api/scene/PonderStoryBoard.java)
program(SceneBuilder, SceneBuildingUtil) functional interface.

<a id="p-section"></a>
## p-section
[common/src/main/java/net/createmod/ponder/foundation/element/WorldSectionElementImpl.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/element/WorldSectionElementImpl.java)
Section geometry, per-layer caches, transforms, block entities and selection.

<a id="p-level"></a>
## p-level
[common/src/main/java/net/createmod/ponder/api/level/PonderLevel.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/api/level/PonderLevel.java)
Isolated schematic world and virtual rendering support.

<a id="p-animate"></a>
## p-animate
[common/src/main/java/net/createmod/ponder/foundation/instruction/AnimateElementInstruction.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/instruction/AnimateElementInstruction.java)
Linear delta interpolation, nonblocking animation.

<a id="p-move"></a>
## p-move
[common/src/main/java/net/createmod/ponder/foundation/instruction/AnimateWorldSectionInstruction.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/instruction/AnimateWorldSectionInstruction.java)
Translation and Euler-rotation adapters; zero-duration force update.

<a id="p-ticking"></a>
## p-ticking
[common/src/main/java/net/createmod/ponder/foundation/instruction/TickingInstruction.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/instruction/TickingInstruction.java)
Remaining ticks, completion and blocking behavior.

<a id="p-ui"></a>
## p-ui
[common/src/main/java/net/createmod/ponder/foundation/ui/PonderUI.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/ui/PonderUI.java)
Playback and inspection interface; relevant render excerpts examined.

<a id="p-debug"></a>
## p-debug
[common/src/main/java/net/createmod/ponder/foundation/content/DebugScenes.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/content/DebugScenes.java)
Reference for simultaneous movement/rotation; search excerpts only.

<a id="p-registry"></a>
## p-registry
[common/src/main/java/net/createmod/ponder/foundation/registration/PonderSceneRegistry.java](https://github.com/Creators-of-Create/Ponder/blob/89819291b726708d119b118dea01667eae0b64c9/common/src/main/java/net/createmod/ponder/foundation/registration/PonderSceneRegistry.java)
Schematic/storyboard registry; search excerpts only.

<a id="c-license"></a>
## c-license
[LICENSE.md](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/LICENSE.md)
MIT code; assets directory explicitly excluded.

<a id="c-registry"></a>
## c-registry
[src/main/java/com/simibubi/create/infrastructure/ponder/AllCreatePonderScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/AllCreatePonderScenes.java)
Item-to-storyboard registry. mechanical_piston/anchor maps to PistonScenes::movement.

<a id="c-builder"></a>
## c-builder
[src/main/java/com/simibubi/create/foundation/ponder/CreateSceneBuilder.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/foundation/ponder/CreateSceneBuilder.java)
Create-specific kinetic, belt, block-entity and virtual-world helpers.

<a id="c-armscenes"></a>
## c-armscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ArmScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ArmScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-bearingscenes"></a>
## c-bearingscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/BearingScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/BearingScenes.java)
Representative methods read and analyzed.

<a id="c-beltscenes"></a>
## c-beltscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/BeltScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/BeltScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-cartassemblerscenes"></a>
## c-cartassemblerscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/CartAssemblerScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/CartAssemblerScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-chaindrivescenes"></a>
## c-chaindrivescenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ChainDriveScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ChainDriveScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-chassisscenes"></a>
## c-chassisscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ChassisScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ChassisScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-chutescenes"></a>
## c-chutescenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ChuteScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ChuteScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-crafterscenes"></a>
## c-crafterscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/CrafterScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/CrafterScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-deployerscenes"></a>
## c-deployerscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/DeployerScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/DeployerScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-detectorscenes"></a>
## c-detectorscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/DetectorScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/DetectorScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-displayscenes"></a>
## c-displayscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/DisplayScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/DisplayScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-ejectorscenes"></a>
## c-ejectorscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/EjectorScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/EjectorScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-elevatorscenes"></a>
## c-elevatorscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ElevatorScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ElevatorScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-fanscenes"></a>
## c-fanscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/FanScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/FanScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-funnelscenes"></a>
## c-funnelscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/FunnelScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/FunnelScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-gantryscenes"></a>
## c-gantryscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/GantryScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/GantryScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-itemvaultscenes"></a>
## c-itemvaultscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ItemVaultScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ItemVaultScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-kineticsscenes"></a>
## c-kineticsscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/KineticsScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/KineticsScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-mechanicaldrillscenes"></a>
## c-mechanicaldrillscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/MechanicalDrillScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/MechanicalDrillScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-mechanicalsawscenes"></a>
## c-mechanicalsawscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/MechanicalSawScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/MechanicalSawScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-movementactorscenes"></a>
## c-movementactorscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/MovementActorScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/MovementActorScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-pistonscenes"></a>
## c-pistonscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/PistonScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/PistonScenes.java)
Representative methods read and analyzed.

<a id="c-processingscenes"></a>
## c-processingscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ProcessingScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/ProcessingScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-pulleyscenes"></a>
## c-pulleyscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/PulleyScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/PulleyScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-redstonescenes"></a>
## c-redstonescenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/RedstoneScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/RedstoneScenes.java)
Representative methods read and analyzed.

<a id="c-redstonescenes2"></a>
## c-redstonescenes2
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/RedstoneScenes2.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/RedstoneScenes2.java)
Directory entry verified; body not exhaustively audited.

<a id="c-rollerscenes"></a>
## c-rollerscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/RollerScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/RollerScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-steamscenes"></a>
## c-steamscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/SteamScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/SteamScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-templatescenes"></a>
## c-templatescenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/TemplateScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/TemplateScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-tunnelscenes"></a>
## c-tunnelscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/TunnelScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/TunnelScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-drainscenes"></a>
## c-drainscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/DrainScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/DrainScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-fluidmanipulationscenes"></a>
## c-fluidmanipulationscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/FluidManipulationScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/FluidManipulationScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-fluidtankscenes"></a>
## c-fluidtankscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/FluidTankScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/FluidTankScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-pipescenes"></a>
## c-pipescenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/PipeScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/PipeScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-pumpscenes"></a>
## c-pumpscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/PumpScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/PumpScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-spoutscenes"></a>
## c-spoutscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/SpoutScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/fluid/SpoutScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-factorygaugescenes"></a>
## c-factorygaugescenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/FactoryGaugeScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/FactoryGaugeScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-packagerscenes"></a>
## c-packagerscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/PackagerScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/PackagerScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-repackagerscenes"></a>
## c-repackagerscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/RepackagerScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/RepackagerScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-stocklinkscenes"></a>
## c-stocklinkscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/StockLinkScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/StockLinkScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-stocktickerscenes"></a>
## c-stocktickerscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/StockTickerScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/StockTickerScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-tableclothscenes"></a>
## c-tableclothscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/TableClothScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/highLogistics/TableClothScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-trackobserverscenes"></a>
## c-trackobserverscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrackObserverScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrackObserverScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-trackscenes"></a>
## c-trackscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrackScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrackScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-trainscenes"></a>
## c-trainscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrainScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrainScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-trainsignalscenes"></a>
## c-trainsignalscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrainSignalScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrainSignalScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="c-trainstationscenes"></a>
## c-trainstationscenes
[src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrainStationScenes.java](https://github.com/Creators-of-Create/Create/blob/fc9535d82a29419164a1e9dc9c678bdcddeab30d/src/main/java/com/simibubi/create/infrastructure/ponder/scenes/trains/TrainStationScenes.java)
Directory entry verified; body not exhaustively audited.

<a id="b-redstone"></a>
## b-redstone
[Code/engine/redstone.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/engine/redstone.py)
PistonMotion, 50 ms logic step, 100 ms movement and interpolated payloads.

<a id="b-models"></a>
## b-models
[Code/engine/piston_models.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/engine/piston_models.py)
Canonical element geometry and UVs, not a replacement animation engine.

<a id="b-model-renderer"></a>
## b-model-renderer
[Code/engine/model_renderer.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/engine/model_renderer.py)
Model-space to renderer-axis mapping; targeted search excerpts.

<a id="b-cache"></a>
## b-cache
[Code/engine/lab_render_cache.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/engine/lab_render_cache.py)
Electrical-only draw-list reuse and retained painter order.

<a id="b-sky"></a>
## b-sky
[Code/engine/skybox.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/engine/skybox.py)
Six-face 3x2 atlas, cached software/native projection, independent drift.

<a id="b-audio"></a>
## b-audio
[Code/engine/audio.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/engine/audio.py)
Predecoded music, preload cache, sequences, MP3 silence trimming.

<a id="b-tutorial"></a>
## b-tutorial
[Code/engine/tutorial_runtime.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/engine/tutorial_runtime.py)
Snapshot-based practice session and existing tutorial progress events.

<a id="b-visual-tests"></a>
## b-visual-tests
[tests/render_visual_checks.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/tests/render_visual_checks.py)
Existing visual checks; read excerpts, not executed here.

<a id="b-integration-tests"></a>
## b-integration-tests
[tests/test_app_integration.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/tests/test_app_integration.py)
Existing integration assertions; read excerpts, not executed here.

<a id="b-redstone-tests"></a>
## b-redstone-tests
[tests/test_redstone.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/tests/test_redstone.py)
In-flight payload regression test located through search.

<a id="b-readme"></a>
## b-readme
[README.md](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/README.md)
Project overview; documentation claims are not independent runtime verification.

<a id="b-handoff"></a>
## b-handoff
[.qa/revision-292-handoff.md](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/.qa/revision-292-handoff.md)
2.9.2 handoff; historical QA claims, not rerun.

<a id="b-app"></a>
## b-app
[Code/blocFantome.py](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/Code/blocFantome.py)
Path verified. Connector could not return the 1,092,830-byte application body.

<a id="v-final"></a>
## v-final
[shaders/final.fsh](https://github.com/JumperOnJava/Voxel-Vibes/blob/cf993c038916b48f9a7ee75ed5d9b718d460a1a2/shaders/final.fsh)
World-coordinate quantization and distance-to-sky fog read directly.

<a id="x-fragment"></a>
## x-fragment
[shaders/program/base_gbuffers/base_fragment.glsl](https://github.com/kolgushev/Pixel-Perfect-B/blob/6703487c1e360503510daf54deee8cd7749afc60/shaders/program/base_gbuffers/base_fragment.glsl)
World-aligned shadow receiver sampling; exact quantization excerpt inspected.

<a id="x-shadow"></a>
## x-shadow
[shaders/lib/shading/get_shadow.glsl](https://github.com/kolgushev/Pixel-Perfect-B/blob/6703487c1e360503510daf54deee8cd7749afc60/shaders/lib/shading/get_shadow.glsl)
Absolute-position-anchored noise sampling excerpt.

<a id="x-language"></a>
## x-language
[shaders/lang/en_US.lang](https://github.com/kolgushev/Pixel-Perfect-B/blob/6703487c1e360503510daf54deee8cd7749afc60/shaders/lang/en_US.lang)
Author describes pixelated shadows and Complementary inspiration.

<a id="v-project"></a>
## v-project
[Voxel Vibes project page](https://modrinth.com/shader/voxel-vibes)
Published feature list and GPL declaration; a GPU shader reference, not a CPU library.

<a id="sh-fog"></a>
## sh-fog
[Silent Hill 2 Enhanced Edition comparison](https://enhanced.townofsilenthill.com/SH2/compare.htm#fog)
Maintainer comparison. Older platform comparison, not a current performance benchmark or original Team Silent postmortem.

<a id="sky-cloud-cube"></a>
## sky-cloud-cube
[Cloudy Skyboxes · cubemaps](https://opengameart.org/content/cloudy-skyboxes-0)
Publisher describes 25 skies in two projections; one sentence says 32 files per pack, so archive member count remains unverified. Convert the cross layout to Bloc 3×2.

<a id="sky-cloud-pano"></a>
## sky-cloud-pano
[Cloudy Skyboxes · panoramas](https://opengameart.org/content/cloudy-skyboxes-0)
Alternative to cubemaps, not an additional 25 unique skies. Choose one projection rather than download both automatically.

<a id="sky-space"></a>
## sky-space
[Space Skyboxes](https://opengameart.org/content/space-skyboxes-0)
Correct author for this exact OpenGameArt URL is StumpyStrust, not Screaming Brain Studios. Published bkg.zip is about 122.3 MB; page-only, deliberately excluded from automatic bulk fetch.

<a id="sky-kenney"></a>
## sky-kenney
[Skybox Pack](https://kenney.nl/assets/skybox-pack)
Earlier page inspection reported CC0 and 22 files. A later fetch failed; exact package contents and current direct URL remain unresolved. Page-only.

<a id="sky-qwantani"></a>
## sky-qwantani
[Qwantani Dusk 2 (Pure Sky)](https://polyhaven.com/a/qwantani_dusk_2_puresky)
Sky-only photographic source. A web preview was visually inspected, not decoded locally or checked for cubemap seams. Choose a lower resolution through the page to avoid its large default HDR/EXR download.

<a id="sky-kloppenheim06"></a>
## sky-kloppenheim06
[Kloppenheim 06 (Pure Sky)](https://polyhaven.com/a/kloppenheim_06_puresky)
Sky-only source. Page describes warm rays and scattered cloud. Metadata-only curation; not a downloaded/converted atlas.

<a id="sky-satara"></a>
## sky-satara
[Satara Night](https://polyhaven.com/a/satara_night)
Visually inspected web image: bright village lights, huts and trees remain at the horizon. Not a pure sky. Reframe/edit before using as an isolated void backdrop.

<a id="sky-moonlit"></a>
## sky-moonlit
[Moonlit Golf](https://polyhaven.com/a/moonlit_golf)
Not a pure sky: field and trees remain. Page publishes a tonemapped JPEG option; no local decode or seam review.

<a id="music-xb2"></a>
## music-xb2
[Xenoblade Chronicles 2 official soundtrack catalogue](https://www.procyon-studio.co.jp/special/xbostportal/en/xb2ost.html)
Exact compositions and per-track credits checked against current official list.

<a id="music-zelda"></a>
## music-zelda
[Zelda & Piano: Ocarina of Time](https://gamechops.com/zeldapiano2/)
GameChops: Super Piano 64 solo-piano arrangements; original composer Koji Kondo.

<a id="music-c418"></a>
## music-c418
[Minecraft - Volume Alpha](https://c418.bandcamp.com/album/minecraft-volume-alpha)
Artist release and download page; track names/durations verified.

<a id="music-celeste"></a>
## music-celeste
[Celeste Original Soundtrack](https://radicaldreamland.bandcamp.com/album/celeste-original-soundtrack)
Lena Raine artist release; Awake is the selected candidate.

<a id="ui-kenney"></a>
## ui-kenney
[UI Audio](https://kenney.nl/assets/ui-audio)
50 files per publisher. Dry button/switch/click reference, not automatically the desired ethereal final set.

<a id="ui-impact"></a>
## ui-impact
[Impact Sounds](https://kenney.nl/assets/impact-sounds)
130 foley files per publisher. Audition quiet physical contacts; no individual member filenames were inspected.

<a id="ui-chimes"></a>
## ui-chimes
[Wind Chimes](https://opengameart.org/content/wind-chimes)
Three approximately three-minute loops, not a UI one-shot pack. Useful as a resonance audition source; original files remain unedited.

<a id="ui-infographics"></a>
## ui-infographics
[Interface & Infographics](https://sonniss.com/sound-effects/interface-infographics/)
117 designed stereo files, 24-bit/96kHz, 99.3 MB. Named synth hardware and glass/chime/pluck tags. Preview/acquisition page only; not purchased or redistributed.

<a id="v-license"></a>
## v-license
[LICENSE.txt](https://github.com/JumperOnJava/Voxel-Vibes/blob/cf993c038916b48f9a7ee75ed5d9b718d460a1a2/LICENSE.txt)
License path identified in repository listing. Retrieve alongside source.

<a id="x-license"></a>
## x-license
[LICENSE](https://github.com/kolgushev/Pixel-Perfect-B/blob/6703487c1e360503510daf54deee8cd7749afc60/LICENSE)
License path identified in repository listing. Retrieve alongside source.

<a id="b-license"></a>
## b-license
[LICENSE](https://github.com/IsolatedSingularity/Bloc-Fantome/blob/0391259c5ebc0519feb324477fdc1f62bc66ccb7/LICENSE)
License path identified in repository listing. Retrieve alongside source.
