# Source map and retrieval boundary

Ponder pin: `89819291b726708d119b118dea01667eae0b64c9`. Create pin: `fc9535d82a29419164a1e9dc9c678bdcddeab30d`. Full upstream URLs, ownership notes and coverage labels are in [SOURCES](../SOURCES.md) and [source_manifest.json](../scripts/source_manifest.json).

| Question | First source |
|---|---|
| What does one storyboard implement? | `api/scene/PonderStoryBoard.java` |
| What is queued and what blocks? | `foundation/PonderSceneBuilder.java`, `foundation/PonderScene.java`, `instruction/TickingInstruction.java` |
| Is section movement eased? | `instruction/AnimateElementInstruction.java`, `AnimateWorldSectionInstruction.java` |
| How are geometry, pivots and picking related? | `element/WorldSectionElementImpl.java` |
| How are block entities rendered in an isolated world? | `api/level/PonderLevel.java`, section implementation |
| How do reset and seeking work? | `foundation/PonderScene.java` |
| Which helpers belong to Create rather than Ponder? | Create's `foundation/ponder/CreateSceneBuilder.java` |
| Which item opens which scene? | Create's `infrastructure/ponder/AllCreatePonderScenes.java` |
| Where is the piston choreography? | Create's `infrastructure/ponder/scenes/PistonScenes.java` |

Ponder paths in the table are relative to `common/src/main/java/net/createmod/ponder/`. Create Java paths are relative to `src/main/java/com/simibubi/create/`.

## Exactly what fetching means

The default source workflow fetches selected text files, including upstream license notices, at immutable commits. It does not clone histories, run Gradle, install Minecraft, extract a game JAR, import textures, or execute downloaded source. Scene `.nbt` files are not included in the automatic source set because Create's resource assets have a separate rights scope. The registered piston set's known asset path is `src/main/resources/assets/create/ponder/mechanical_piston/anchor.nbt`; it is a starting structure, not a portable renderer.

Downloading these files provides an agent with code to read. It does not produce a runnable Ponder installation. Running Ponder itself requires compatible Minecraft/mod-loader dependencies and associated resources; those build dependencies were not assembled in this research-only run.
