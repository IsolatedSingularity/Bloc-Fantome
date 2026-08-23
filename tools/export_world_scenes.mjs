// Build the bundled Bloc Fantome world scenes from the version-locked
// Minecraft-Generation viewer corpus. This is a development tool: the app
// loads the generated gzip files and has no Node or sibling-repository runtime
// dependency.

import { createRequire } from "node:module"
import { mkdir, readFile, writeFile } from "node:fs/promises"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"
import { gzipSync } from "node:zlib"

const here = dirname(fileURLToPath(import.meta.url))
const repo = resolve(here, "..")
const onlyArg = process.argv.find(argument => argument.startsWith("--only="))
const selectedIds = new Set(
  (onlyArg?.slice("--only=".length) ?? "").split(",").filter(Boolean)
)
const shouldWrite = id => selectedIds.size === 0 || selectedIds.has(id)
const generationArg = process.argv.slice(2).find(argument => !argument.startsWith("--"))
const generationRepo = resolve(generationArg ?? join(repo, "..", "Minecraft-Generation"))
const viewer = join(generationRepo, "Viewer")
const requireFromViewer = createRequire(join(viewer, "package.json"))
const { unzipSync } = requireFromViewer("fflate")

const { readStructure } = await import(pathToFileURL(join(viewer, "src", "nbt.js")))
const { runJigsaw } = await import(pathToFileURL(join(viewer, "src", "jigsaw.js")))
const { runEndCity } = await import(pathToFileURL(join(viewer, "src", "generators", "endcity.js")))
const { buildProcessorIndex, applyProcessors, seedFor } = await import(
  pathToFileURL(join(viewer, "src", "processors.js"))
)
const { generateFeature } = await import(pathToFileURL(join(viewer, "src", "features", "index.js")))
const { EMPTY, mix, normStatesDeep, poolTemplates, rnd, shuffle } = await import(
  pathToFileURL(join(viewer, "src", "transforms.js"))
)

const td = new TextDecoder()
const outDir = join(repo, "Code", "worlds")
const structureOutDir = join(repo, "Code", "saves")

async function zipMap(path) {
  return unzipSync(new Uint8Array(await readFile(path)))
}

const classic = await zipMap(join(
  generationRepo, "Assets", "minecraft_1_16_1", "viewer", "client_structure_assets.zip"
))
const classicWorldgen = await zipMap(join(
  generationRepo, "Assets", "minecraft_1_16_1", "viewer", "worldgen_registry.zip"
))
const later = await zipMap(join(
  generationRepo, "Assets", "minecraft_later_versions", "viewer", "structure_assets.zip"
))

const strip = ref => ref.replace(/^minecraft:/, "").replace(/^minecraft\//, "")
const jsonAt = (map, path) => map[path] ? JSON.parse(td.decode(map[path])) : null

function dataReader(...maps) {
  return async path => {
    for (const map of maps) {
      const json = jsonAt(map, path)
      if (json) return normStatesDeep(json)
    }
    return null
  }
}

function structureRels(map, folder) {
  const expression = new RegExp(`^data/([^/]+)/${folder}/(.+)\\.nbt$`)
  return Object.keys(map).map(key => {
    const match = key.match(expression)
    return match ? `${match[1]}/${match[2]}` : null
  }).filter(Boolean)
}

function structureLoader(map, folder, processorIndex = null, seed = 0) {
  const cache = new Map()
  return async ref => {
    const name = strip(ref)
    if (!cache.has(name)) {
      const bytes = map[`data/minecraft/${folder}/${name}.nbt`]
      cache.set(name, (async () => {
        let structure = bytes ? await readStructure(bytes) : null
        if (!structure) return null
        const rel = `minecraft/${name}`
        const entry = processorIndex?.get(rel)
        if (entry) {
          structure = await applyProcessors(
            structure, entry, rnd(mix(seed, seedFor(rel))),
            overlay => structureLoader(map, folder, null, seed)(overlay),
          )
        }
        return structure
      })())
    }
    return cache.get(name)
  }
}

function poolLoader(map) {
  return async ref => jsonAt(
    map,
    `data/minecraft/worldgen/template_pool/${strip(ref)}.json`,
  )
}

function featureLoader(worldgen, loadStruct) {
  const readJson = dataReader(worldgen)
  const pathFor = ref => ref.includes(":") ? ref.replace(":", "/") : `minecraft/${ref}`
  const readFeature = async ref => {
    const rel = pathFor(ref)
    const slash = rel.indexOf("/")
    const ns = rel.slice(0, slash), path = rel.slice(slash + 1)
    return await readJson(`data/${ns}/worldgen/configured_feature/${path}.json`)
      ?? await readJson(`data/${ns}/worldgen/feature/${path}.json`)
  }
  const resolveFeature = async ref => {
    if (ref == null) return null
    if (typeof ref === "object") {
      if (ref.type === undefined && ref.feature !== undefined) return resolveFeature(ref.feature)
      return ref
    }
    const rel = pathFor(ref)
    const slash = rel.indexOf("/")
    const ns = rel.slice(0, slash), path = rel.slice(slash + 1)
    const placed = await readJson(`data/${ns}/worldgen/placed_feature/${path}.json`)
    return placed?.feature !== undefined ? resolveFeature(placed.feature) : readFeature(rel)
  }
  const loadProcessors = async ref => {
    const rel = pathFor(ref)
    const slash = rel.indexOf("/")
    const ns = rel.slice(0, slash), path = rel.slice(slash + 1)
    const json = await readJson(`data/${ns}/worldgen/processor_list/${path}.json`)
    return json?.processors ?? []
  }
  return async (ref, seed) => {
    const json = await readFeature(ref)
    if (!json) return null
    return generateFeature(pathFor(ref), json, rnd(seed), resolveFeature, loadStruct, null, loadProcessors)
  }
}

async function jigsawAssembly({ assets, folder, worldgen, startPool, depth, radius, seed, aliases = {} }) {
  const readJson = dataReader(worldgen, assets)
  const processorIndex = await buildProcessorIndex(
    [...new Set([...Object.keys(worldgen), ...Object.keys(assets)])],
    readJson,
    structureRels(assets, folder),
  )
  const loadStruct = structureLoader(assets, folder, processorIndex, seed)
  const basePoolLoader = poolLoader(worldgen)
  const loadPool = ref => basePoolLoader(aliases[ref] ?? aliases[strip(ref)] ?? ref)
  const loadFeature = featureLoader(worldgen, loadStruct)
  const pool = await loadPool(startPool)
  const candidates = shuffle(poolTemplates(pool), rnd(seed)).filter(item => item !== EMPTY)
  if (!candidates.length) throw new Error(`No start piece in ${startPool}`)
  const start = await loadStruct(candidates[0])
  if (!start) throw new Error(`Missing start structure ${candidates[0]}`)
  const result = await runJigsaw(start, {
    loadStruct,
    loadPool,
    loadFeature,
    maxDepth: depth,
    maxPieces: 1024,
    maxRadius: radius,
    levelSeed: level => mix(seed, level),
    keepJigsaws: false,
  })
  return result.structure
}

const exactNames = new Set([
  "air", "grass_block", "dirt", "stone", "cobblestone", "gravel", "sand", "clay",
  "oak_log", "oak_planks", "oak_leaves", "birch_log", "birch_planks", "birch_leaves",
  "spruce_log", "spruce_planks", "spruce_leaves", "dark_oak_log", "dark_oak_planks",
  "dark_oak_leaves", "acacia_log", "acacia_planks", "acacia_leaves", "jungle_log",
  "jungle_planks", "jungle_leaves", "obsidian", "crying_obsidian", "end_stone",
  "end_stone_bricks", "purpur_block", "purpur_pillar", "bedrock", "netherrack",
  "soul_sand", "soul_soil", "blackstone", "polished_blackstone",
  "polished_blackstone_bricks", "chiseled_polished_blackstone",
  "cracked_polished_blackstone_bricks", "gilded_blackstone", "basalt", "polished_basalt",
  "smooth_basalt", "nether_bricks", "nether_gold_ore", "ancient_debris", "gold_block",
  "iron_block", "diamond_block", "chest",
  "deepslate", "cobbled_deepslate", "polished_deepslate", "deepslate_bricks",
  "cracked_deepslate_bricks", "deepslate_tiles", "cracked_deepslate_tiles",
  "chiseled_deepslate", "reinforced_deepslate", "sculk", "sculk_catalyst",
  "sculk_shrieker", "sculk_sensor", "gray_wool", "cyan_wool", "blue_wool",
  "light_blue_wool", "white_wool", "red_wool", "glass", "water", "lava",
  "tuff", "polished_tuff", "tuff_bricks", "chiseled_tuff", "chiseled_tuff_bricks",
  "grass_path", "farmland", "wheat", "smooth_sandstone", "cut_sandstone",
  "powder_snow", "glass_pane", "ladder", "chain", "lantern", "soul_lantern",
  "redstone_lamp", "vault", "decorated_pot",
  "spruce_stairs", "acacia_stairs", "purpur_stairs", "deepslate_brick_stairs",
  "deepslate_tile_stairs", "cobbled_deepslate_stairs", "polished_deepslate_stairs",
  "blackstone_stairs", "polished_blackstone_brick_stairs",
  "spruce_slab", "acacia_slab", "purpur_slab", "deepslate_brick_slab",
  "deepslate_tile_slab", "cobbled_deepslate_slab", "polished_deepslate_slab",
  "blackstone_slab", "polished_blackstone_brick_slab",
  "spruce_door", "acacia_door", "jungle_door",
  "chorus_plant", "chorus_flower", "crimson_fungus", "warped_fungus",
  "nether_sprouts", "twisting_vines", "weeping_vines",
  "smooth_sandstone_slab", "sandstone_slab", "smooth_sandstone_stairs",
  "sandstone_stairs", "smooth_stone_slab", "polished_tuff_slab",
  "smooth_quartz_slab", "granite_stairs", "polished_deepslate_wall",
  "deepslate_tile_wall", "cobblestone_wall", "sandstone_wall",
  "deepslate_brick_wall", "blackstone_wall", "diorite_wall", "granite_wall",
  "spruce_fence", "acacia_fence", "oak_fence", "dark_oak_fence",
  "jungle_fence", "oak_fence_gate", "spruce_trapdoor", "oak_trapdoor",
  "candle", "white_candle", "red_candle", "wall_torch",
  "white_bed", "yellow_bed", "green_bed", "red_bed", "lime_bed",
  "cyan_bed", "blue_bed", "purple_bed", "orange_bed", "brown_bed",
  "cobblestone_stairs", "brown_wall_banner", "magenta_wall_banner",
  "redstone_wall_torch",
])

const aliases = {
  grass_block: "GRASS",
  grass_path: "DIRT_PATH",
  snow: "SNOW",
  snow_block: "SNOW",
  glowstone: "GLOWSTONE",
  magma_block: "MAGMA_BLOCK",
  spawner: "MOB_SPAWNER",
  end_rod: "SEA_LANTERN",
  shulker_box: "PURPUR_BLOCK",
  polished_blackstone_brick_stairs: "POLISHED_BLACKSTONE_BRICKS",
  polished_blackstone_brick_slab: "POLISHED_BLACKSTONE_BRICKS",
  polished_blackstone_brick_wall: "POLISHED_BLACKSTONE_BRICKS",
  blackstone_stairs: "BLACKSTONE",
  blackstone_slab: "BLACKSTONE",
  blackstone_wall: "BLACKSTONE",
  polished_blackstone_stairs: "POLISHED_BLACKSTONE",
  polished_blackstone_slab: "POLISHED_BLACKSTONE",
  polished_blackstone_wall: "POLISHED_BLACKSTONE",
  chain: "IRON_BLOCK",
  lantern: "SEA_LANTERN",
  soul_lantern: "SEA_LANTERN",
  nether_brick_stairs: "NETHER_BRICKS",
  nether_brick_slab: "NETHER_BRICKS",
  nether_brick_wall: "NETHER_BRICKS",
  purpur_stairs: "PURPUR_BLOCK",
  purpur_slab: "PURPUR_BLOCK",
  deepslate_brick_stairs: "DEEPSLATE_BRICKS",
  deepslate_brick_slab: "DEEPSLATE_BRICKS",
  deepslate_brick_wall: "DEEPSLATE_BRICKS",
  deepslate_tile_stairs: "DEEPSLATE_TILES",
  deepslate_tile_slab: "DEEPSLATE_TILES",
  deepslate_tile_wall: "DEEPSLATE_TILES",
  cobbled_deepslate_stairs: "COBBLED_DEEPSLATE",
  cobbled_deepslate_slab: "COBBLED_DEEPSLATE",
  cobbled_deepslate_wall: "COBBLED_DEEPSLATE",
  polished_deepslate_stairs: "POLISHED_DEEPSLATE",
  polished_deepslate_slab: "POLISHED_DEEPSLATE",
  polished_deepslate_wall: "POLISHED_DEEPSLATE",
  soul_fire: "SOUL_FIRE",
  waxed_copper_block: "COPPER_BLOCK",
  waxed_oxidized_copper: "OXIDIZED_COPPER",
  waxed_oxidized_cut_copper: "OXIDIZED_CUT_COPPER",
  waxed_cut_copper: "CUT_COPPER",
  waxed_exposed_copper_bulb: "EXPOSED_COPPER_BULB",
  waxed_weathered_copper_bulb: "WEATHERED_COPPER_BULB",
  waxed_oxidized_copper_bulb: "OXIDIZED_COPPER_BULB",
  waxed_copper_bulb: "COPPER_BULB",
  waxed_copper_grate: "COPPER_GRATE",
  waxed_oxidized_copper_grate: "OXIDIZED_COPPER_GRATE",
  waxed_chiseled_copper: "CUT_COPPER",
  waxed_oxidized_chiseled_copper: "OXIDIZED_CUT_COPPER",
  waxed_cut_copper_slab: "CUT_COPPER_SLAB",
  waxed_oxidized_cut_copper_stairs: "OXIDIZED_CUT_COPPER_STAIRS",
  waxed_oxidized_copper_trapdoor: "OXIDIZED_COPPER_TRAPDOOR",
  oxidized_copper_trapdoor: "OXIDIZED_COPPER_TRAPDOOR",
  waxed_oxidized_copper_door: "OXIDIZED_COPPER",
  waxed_copper_door: "COPPER_BLOCK",
  gray_carpet: "GRAY_WOOL", blue_carpet: "BLUE_WOOL", cyan_carpet: "CYAN_WOOL",
  light_blue_carpet: "LIGHT_BLUE_WOOL", green_carpet: "GREEN_WOOL",
  purple_carpet: "PURPLE_WOOL", white_carpet: "WHITE_WOOL",
  stripped_spruce_log: "STRIPPED_SPRUCE_LOG", stripped_spruce_wood: "STRIPPED_SPRUCE_LOG",
  stripped_oak_log: "STRIPPED_OAK_LOG", stripped_oak_wood: "STRIPPED_OAK_LOG",
  stripped_acacia_log: "STRIPPED_ACACIA_LOG", acacia_wood: "ACACIA_LOG",
  spruce_wood: "SPRUCE_LOG", grass: "GRASS", tall_grass: "GRASS", large_fern: "GRASS",
  fern: "GRASS", poppy: "RED_WOOL", dandelion: "YELLOW_WOOL",
  spruce_trapdoor: "SPRUCE_TRAPDOOR", oak_trapdoor: "OAK_TRAPDOOR",
  spruce_fence: "SPRUCE_FENCE", acacia_fence: "ACACIA_FENCE",
  oak_fence: "OAK_FENCE", dark_oak_fence: "DARK_OAK_FENCE",
  jungle_fence: "JUNGLE_FENCE", oak_fence_gate: "OAK_FENCE_GATE",
  orange_terracotta: "ORANGE_TERRACOTTA", yellow_terracotta: "YELLOW_TERRACOTTA",
  white_terracotta: "WHITE_TERRACOTTA", terracotta: "TERRACOTTA",
  magenta_stained_glass: "MAGENTA_STAINED_GLASS",
  white_stained_glass: "WHITE_STAINED_GLASS", black_stained_glass: "BLACK_STAINED_GLASS",
  light_gray_wool: "LIGHT_GRAY_WOOL", packed_ice: "PACKED_ICE", blue_ice: "PACKED_ICE",
  oak_door: "OAK_DOOR", furnace: "FURNACE", crafting_table: "CRAFTING_TABLE",
  pumpkin: "PUMPKIN", melon: "MELON", sandstone: "SANDSTONE", diorite: "DIORITE",
  granite: "GRANITE", quartz_block: "QUARTZ_BLOCK", target: "TARGET",
  ender_chest: "ENDER_CHEST", smooth_stone: "SMOOTH_STONE",
  redstone_block: "REDSTONE_BLOCK", redstone_wire: "REDSTONE_BLOCK",
  dispenser: "FURNACE", smoker: "FURNACE", blast_furnace: "FURNACE",
  barrel: "CHEST", composter: "OAK_PLANKS", campfire: "OAK_LOG",
  white_bed: "WHITE_BED", yellow_bed: "YELLOW_BED", green_bed: "GREEN_BED",
  red_bed: "RED_BED", lime_bed: "LIME_BED", cyan_bed: "CYAN_BED",
  blue_bed: "BLUE_BED", purple_bed: "PURPLE_BED", orange_bed: "ORANGE_BED",
  brown_bed: "BROWN_BED", red_glazed_terracotta: "RED_TERRACOTTA",
  orange_glazed_terracotta: "ORANGE_TERRACOTTA", oxidized_cut_copper: "OXIDIZED_CUT_COPPER",
}

function appType(name) {
  const short = name.replace(/^minecraft:/, "")
  const exact = short.toUpperCase()
  if (exactNames.has(short) && !["GRASS_BLOCK", "GRASS_PATH"].includes(exact)) return exact
  if (aliases[short]) return aliases[short]
  if (short.endsWith("_stairs")) return short.includes("oak") ? "OAK_STAIRS" : "STONE_BRICKS"
  if (short.endsWith("_slab")) return short.includes("oak") ? "OAK_SLAB" : "STONE_SLAB"
  if (short.endsWith("_wall")) return "STONE_BRICKS"
  if (short.includes("candle") || short.includes("torch") || short.includes("lantern")) return "SEA_LANTERN"
  if (short.includes("skull") || short.includes("head")) return "BONE_BLOCK"
  if (short.includes("deepslate")) return "DEEPSLATE"
  if (short.includes("sculk")) return "SCULK"
  return "STONE"
}

function terrainHeight(x, y, seed, base, amplitude) {
  const wave = Math.sin((x + seed % 19) * 0.105) + Math.cos((y - seed % 23) * 0.087)
  const detail = Math.sin((x + y) * 0.047 + seed) * 0.7
  return Math.round(base + (wave + detail) * amplitude)
}

function hash2(x, y, seed) {
  let value = Math.imul(x ^ seed, 0x1f123bb5) ^ Math.imul(y + seed, 0x5f356495)
  value ^= value >>> 15
  value = Math.imul(value, 0x2c1b3c6d)
  value ^= value >>> 12
  return (value >>> 0) / 0xffffffff
}

function addTerrain(blocks, occupied, kind, seed, minY, foundation = null) {
  const put = (x, y, z, type, minecraft) => {
    const key = `${x},${y},${z}`
    if (occupied.has(key)) return
    occupied.add(key)
    blocks.push({ x, y, z, type, minecraft, state: {}, role: "terrain" })
  }
  const nether = [
    "nether_wastes", "soul_sand_valley", "crimson_forest",
    "warped_forest", "basalt_deltas",
  ].includes(kind)
  const village = ["plains", "desert", "savanna", "taiga", "snowy"].includes(kind)
  const radius = kind === "end" ? 76 : nether ? 68 : 72
  const center = 128
  const tops = new Map()
  for (let x = center - radius; x <= center + radius; x++) {
    for (let y = center - radius; y <= center + radius; y++) {
      const dx = x - center, dy = y - center
      const distance = Math.hypot(dx, dy)
      if (kind === "end" && distance > radius + Math.sin((x + y) * 0.19) * 8) continue
      if (nether && distance > radius + Math.sin((x - y) * 0.15) * 5) continue
      const base = kind === "ancient" ? -30 : kind === "end" ? 14 : nether ? 30 : village ? 62 : 56
      const amplitude = kind === "end" ? 2.5 : nether ? 6.5 : village ? 3.5 : 3.0
      let height = terrainHeight(x, y, seed, base, amplitude)
      if (
        kind === "end" && foundation
        && x >= foundation.minX && x <= foundation.maxX
        && y >= foundation.minY && y <= foundation.maxY
      ) height = foundation.top
      if (nether && hash2(Math.floor(x / 7), Math.floor(y / 7), seed) > 0.88) height -= 4
      const top = kind === "end" ? "END_STONE"
        : kind === "ancient" ? "SCULK"
        : kind === "desert" ? "SAND"
        : kind === "soul_sand_valley" ? (hash2(x, y, seed) > 0.48 ? "SOUL_SOIL" : "SOUL_SAND")
        : kind === "crimson_forest" ? "CRIMSON_NYLIUM"
        : kind === "warped_forest" ? "WARPED_NYLIUM"
        : kind === "basalt_deltas" ? (hash2(x, y, seed) > 0.36 ? "BASALT" : "BLACKSTONE")
        : village ? "GRASS" : "NETHERRACK"
      const minecraft = kind === "end" ? "minecraft:end_stone"
        : kind === "ancient" ? "minecraft:sculk"
        : kind === "desert" ? "minecraft:sand"
        : kind === "soul_sand_valley" ? `minecraft:${top.toLowerCase()}`
        : kind === "crimson_forest" ? "minecraft:crimson_nylium"
        : kind === "warped_forest" ? "minecraft:warped_nylium"
        : kind === "basalt_deltas" ? `minecraft:${top.toLowerCase()}`
        : village ? "minecraft:grass_block" : "minecraft:netherrack"
      const fillType = village && kind !== "desert" ? "DIRT"
        : kind === "ancient" ? "DEEPSLATE"
        : nether ? "NETHERRACK" : top
      const fillName = village && kind !== "desert" ? "minecraft:dirt"
        : kind === "ancient" ? "minecraft:deepslate"
        : nether ? "minecraft:netherrack" : minecraft
      const shellDepth = kind === "end" ? 7 : nether ? 5 : 4
      for (let z = Math.max(minY, height - shellDepth); z < height; z++) put(x, y, z, fillType, fillName)
      put(x, y, height, top, minecraft)
      tops.set(`${x},${y}`, height)
      if (kind === "snowy") put(x, y, height + 1, "SNOW", "minecraft:snow_block")
      if (nether && hash2(x, y, seed ^ 0x1a7a) > 0.986) put(x, y, height + 1, "MAGMA_BLOCK", "minecraft:magma_block")
    }
  }

  const topAt = (x, y) => tops.get(`${x},${y}`)
  const growColumn = (x, y, height, type, minecraft) => {
    const top = topAt(x, y)
    if (top === undefined) return
    for (let z = top + 1; z <= top + height; z++) put(x, y, z, type, minecraft)
  }
  for (let x = center - radius + 5; x <= center + radius - 5; x++) {
    for (let y = center - radius + 5; y <= center + radius - 5; y++) {
      const top = topAt(x, y)
      if (top === undefined || occupied.has(`${x},${y},${top + 1}`)) continue
      const chance = hash2(x, y, seed ^ 0x51f15e)
      if (kind === "end" && chance > 0.994) {
        const height = 3 + Math.floor(hash2(x, y, seed ^ 0xc40a) * 5)
        growColumn(x, y, height, "CHORUS_PLANT", "minecraft:chorus_plant")
        put(x, y, top + height + 1, "CHORUS_FLOWER", "minecraft:chorus_flower")
        if (height > 4) {
          const direction = hash2(x, y, seed ^ 0xa11) > 0.5 ? 1 : -1
          put(x + direction, y, top + height - 1, "CHORUS_PLANT", "minecraft:chorus_plant")
          put(x + direction * 2, y, top + height - 1, "CHORUS_FLOWER", "minecraft:chorus_flower")
        }
      } else if (["crimson_forest", "warped_forest"].includes(kind) && chance > 0.996) {
        const crimson = kind === "crimson_forest"
        const stem = crimson ? "CRIMSON_STEM" : "WARPED_STEM"
        const wart = crimson ? "NETHER_WART_BLOCK" : "WARPED_WART_BLOCK"
        const height = 4 + Math.floor(hash2(x, y, seed ^ 0xf061) * 5)
        growColumn(x, y, height, stem, `minecraft:${stem.toLowerCase()}`)
        for (let ox = -2; ox <= 2; ox++) for (let oy = -2; oy <= 2; oy++) {
          if (Math.abs(ox) + Math.abs(oy) > 3) continue
          put(x + ox, y + oy, top + height, wart, `minecraft:${wart.toLowerCase()}`)
        }
        put(x, y, top + height, "SHROOMLIGHT", "minecraft:shroomlight")
      } else if (kind === "soul_sand_valley" && chance > 0.997) {
        growColumn(x, y, 2 + Math.floor(chance * 4), "BASALT", "minecraft:basalt")
      } else if (kind === "basalt_deltas" && chance > 0.992) {
        growColumn(x, y, 2 + Math.floor(hash2(x, y, seed ^ 0xba5a17) * 7), "BASALT", "minecraft:basalt")
      } else if (village && kind !== "desert" && chance > 0.997) {
        const spruce = kind === "taiga" || kind === "snowy"
        const acacia = kind === "savanna"
        const log = spruce ? "SPRUCE_LOG" : acacia ? "ACACIA_LOG" : "OAK_LOG"
        const leaves = spruce ? "SPRUCE_LEAVES" : acacia ? "ACACIA_LEAVES" : "OAK_LEAVES"
        growColumn(x, y, 4, log, `minecraft:${log.toLowerCase()}`)
        for (let ox = -2; ox <= 2; ox++) for (let oy = -2; oy <= 2; oy++) {
          if (Math.abs(ox) + Math.abs(oy) <= 3) put(x + ox, y + oy, top + 5, leaves, `minecraft:${leaves.toLowerCase()}`)
        }
      }
    }
  }
}

function toScene(structure, spec) {
  const blocks = []
  const occupied = new Set()
  const sx = Math.floor((256 - structure.size[0]) / 2)
  const sy = Math.floor((256 - structure.size[2]) / 2)
  for (const block of structure.blocks) {
    const state = structure.palette[block.state]
    if (!state?.Name || /(^|:)(air|cave_air|void_air|structure_void|structure_block|jigsaw)$/.test(state.Name)) continue
    const x = sx + block.pos[0]
    const y = sy + block.pos[2]
    const z = spec.structureY + block.pos[1]
    if (x < 0 || x >= 256 || y < 0 || y >= 256 || z < spec.minY || z >= spec.minY + spec.height) continue
    occupied.add(`${x},${y},${z}`)
    blocks.push({
      x, y, z,
      type: appType(state.Name),
      minecraft: state.Name,
      state: state.Properties ?? {},
      role: "structure",
    })
  }
  const foundation = spec.habitat === "end" && blocks.length ? {
    minX: Math.min(...blocks.map(block => block.x)) - 2,
    maxX: Math.max(...blocks.map(block => block.x)) + 2,
    minY: Math.min(...blocks.map(block => block.y)) - 2,
    maxY: Math.max(...blocks.map(block => block.y)) + 2,
    top: spec.structureY - 1,
  } : null
  addTerrain(blocks, occupied, spec.habitat, spec.seed, spec.minY, foundation)
  return {
    version: 5,
    dimension: spec.dimension,
    bounds: { width: 256, depth: 256, height: spec.height, min_y: spec.minY },
    scene: {
      kind: "world",
      id: spec.id,
      name: spec.name,
      provider: spec.provider,
      version: spec.version,
      seed: spec.seed,
      source: "Minecraft-Generation Viewer canonical NBT and source-checked assembly",
      accuracy: "faithful deterministic showcase assembly; habitat is representative terrain",
      structure_blocks: structure.blocks.length,
      default_terrain_view: spec.terrainView ?? "all",
      exterior_shell_view: spec.exteriorShellView ?? "original",
    },
    blocks,
  }
}

async function writeScene(spec, structure) {
  if (!shouldWrite(spec.id)) return
  const scene = toScene(structure, spec)
  const path = join(outDir, `${spec.id}.json.gz`)
  await writeFile(path, gzipSync(Buffer.from(JSON.stringify(scene)), { level: 9 }))
  console.log(`${spec.id}: ${scene.blocks.length} cells, ${structure.size.join(" x ")}`)
}

async function writeCursorStructure({ id, name, dimension, pieces, translation = [0, 0, 0], fixedBounds = null }) {
  if (!shouldWrite(id)) return
  const cells = new Map()
  let stackY = 0
  for (const piece of pieces) {
    const structure = await classicLoad(piece.ref)
    if (!structure) throw new Error(`Missing cursor structure piece ${piece.ref}`)
    const offset = piece.offset ?? [0, 0, stackY]
    for (const block of structure.blocks) {
      const state = structure.palette[block.state]
      if (!state?.Name || /(^|:)(air|cave_air|void_air|structure_void|structure_block|jigsaw)$/.test(state.Name)) continue
      const x = block.pos[0] + offset[0]
      const y = block.pos[2] + offset[1]
      const z = block.pos[1] + offset[2]
      cells.set(`${x},${y},${z}`, {
        x, y, z,
        type: appType(state.Name),
        minecraft: state.Name,
        state: state.Properties ?? {},
      })
    }
    if (piece.stack !== false) stackY += Math.max(1, structure.size[1] - 1)
  }
  const raw = [...cells.values()]
  const minX = Math.min(...raw.map(block => block.x))
  const minY = Math.min(...raw.map(block => block.y))
  const minZ = Math.min(...raw.map(block => block.z))
  const blocks = raw.map(block => ({
    ...block,
    x: block.x - minX + translation[0],
    y: block.y - minY + translation[1],
    z: block.z - minZ + translation[2],
  }))
  const width = fixedBounds?.width ?? Math.max(...blocks.map(block => block.x)) + 1
  const depth = fixedBounds?.depth ?? Math.max(...blocks.map(block => block.y)) + 1
  const height = fixedBounds?.height ?? Math.max(...blocks.map(block => block.z)) + 1
  const build = {
    version: 5,
    name,
    dimension,
    bounds: { width, depth, height, min_y: 0 },
    scene: {
      kind: "structure",
      source: "Minecraft Java 1.16.1 canonical structure NBT",
      provider: "version-locked Game Reference assets",
    },
    blocks,
  }
  await writeFile(join(structureOutDir, `${id}.json`), JSON.stringify(build))
  console.log(`${id}: ${blocks.length} canonical cells, ${width} x ${depth} x ${height}`)
}

await mkdir(outDir, { recursive: true })
await mkdir(structureOutDir, { recursive: true })

const classicLoad = structureLoader(classic, "structures")

await writeCursorStructure({
  id: "bastion_bridge_edge", name: "Housing Units Bastion Piece", dimension: "nether",
  pieces: [{ ref: "bastion/units/stages/stage_3_3" }],
})
await writeCursorStructure({
  id: "bastion_remnant_no_lava", name: "Hoglin Stable Bastion Piece", dimension: "nether",
  pieces: [{ ref: "bastion/hoglin_stable/large_stables/outer_0" }],
})
await writeCursorStructure({
  id: "bastion_remnant_with_lava", name: "Treasure Bastion Lava Basin", dimension: "nether",
  pieces: [{ ref: "bastion/treasure/ramparts/lava_basin_main" }],
})
await writeCursorStructure({
  id: "end_city_tower", name: "End City Tower", dimension: "end",
  pieces: [
    { ref: "end_city/tower_base" },
    { ref: "end_city/tower_piece" },
    { ref: "end_city/tower_piece" },
    { ref: "end_city/tower_top" },
  ],
  translation: [3, 3, 3],
  fixedBounds: { width: 16, depth: 16, height: 20 },
})

const endCity = (await runEndCity(classicLoad, { maxDepth: 8, seed: 0x16e0c17 })).structure
await writeScene({
  id: "end_city_1161", name: "End City", provider: "Java source port", version: "1.16.1",
  dimension: "end", habitat: "end", structureY: 19, minY: 0, height: 256, seed: 0x16e0c17,
}, endCity)

const bastion = await jigsawAssembly({
  assets: classic, folder: "structures", worldgen: classicWorldgen,
  startPool: "minecraft:bastion/treasure/starters", depth: 60, radius: 80, seed: 0xba571016,
})
await writeScene({
  id: "bastion_treasure_1161", name: "Treasure Bastion", provider: "Java jigsaw pools", version: "1.16.1",
  dimension: "nether", habitat: "soul_sand_valley", structureY: 31, minY: 0, height: 256, seed: 0xba571016,
}, bastion)

for (const spec of [
  {
    id: "bastion_bridge_1161", name: "Bridge Bastion", startPool: "minecraft:bastion/bridge/start",
    seed: 0xb1d6e116,
  },
  {
    id: "bastion_hoglin_stable_1161", name: "Hoglin Stable Bastion",
    startPool: "minecraft:bastion/hoglin_stable/origin", seed: 0x10611a16,
  },
  {
    id: "bastion_housing_units_1161", name: "Housing Units Bastion",
    startPool: "minecraft:bastion/units/base", seed: 0x0a115116,
  },
]) {
  const structure = await jigsawAssembly({
    assets: classic, folder: "structures", worldgen: classicWorldgen,
    startPool: spec.startPool, depth: 60, radius: 80, seed: spec.seed,
  })
  await writeScene({
    ...spec, provider: "Java jigsaw pools", version: "1.16.1",
    dimension: "nether", habitat: {
      bastion_bridge_1161: "nether_wastes",
      bastion_hoglin_stable_1161: "crimson_forest",
      bastion_housing_units_1161: "warped_forest",
    }[spec.id], structureY: 31, minY: 0, height: 256,
  }, structure)
}

await writeScene({
  id: "basalt_deltas_1161", name: "Basalt Deltas", provider: "Java biome source port",
  version: "1.16.1", dimension: "nether", habitat: "basalt_deltas",
  structureY: 31, minY: 0, height: 256, seed: 0xba5a17,
}, { size: [0, 0, 0], palette: [], blocks: [] })

const ancient = await jigsawAssembly({
  assets: later, folder: "structure", worldgen: later,
  startPool: "minecraft:ancient_city/city_center", depth: 7, radius: 116, seed: 0xac172021,
})
await writeScene({
  id: "ancient_city_121", name: "Ancient City", provider: "Java jigsaw pools", version: "1.21",
  dimension: "overworld", habitat: "ancient", structureY: -27, minY: -64, height: 384, seed: 0xac172021,
  terrainView: "transparent",
}, ancient)

const trialAliases = {
  "minecraft:trial_chambers/spawner/contents/ranged": "minecraft:trial_chambers/spawner/ranged/skeleton",
  "trial_chambers/spawner/contents/ranged": "minecraft:trial_chambers/spawner/ranged/skeleton",
  "minecraft:trial_chambers/spawner/contents/slow_ranged": "minecraft:trial_chambers/spawner/slow_ranged/skeleton",
  "trial_chambers/spawner/contents/slow_ranged": "minecraft:trial_chambers/spawner/slow_ranged/skeleton",
  "minecraft:trial_chambers/spawner/contents/melee": "minecraft:trial_chambers/spawner/melee/zombie",
  "trial_chambers/spawner/contents/melee": "minecraft:trial_chambers/spawner/melee/zombie",
  "minecraft:trial_chambers/spawner/contents/small_melee": "minecraft:trial_chambers/spawner/small_melee/cave_spider",
  "trial_chambers/spawner/contents/small_melee": "minecraft:trial_chambers/spawner/small_melee/cave_spider",
}
const trial = await jigsawAssembly({
  assets: later, folder: "structure", worldgen: later,
  startPool: "minecraft:trial_chambers/chamber/end", depth: 20, radius: 116,
  seed: 0x7a1a121, aliases: trialAliases,
})
await writeScene({
  id: "trial_chamber_121", name: "Trial Chamber", provider: "Java jigsaw pools", version: "1.21",
  dimension: "overworld", habitat: "ancient", structureY: -25, minY: -64, height: 384, seed: 0x7a1a121,
  terrainView: "transparent", exteriorShellView: "glass",
}, trial)

for (const [biome, label, seed] of [
  ["plains", "Plains Village", 0x16a1a501],
  ["desert", "Desert Village", 0x16de5e17],
  ["savanna", "Savanna Village", 0x165a9a11],
  ["taiga", "Taiga Village", 0x167a16a1],
  ["snowy", "Snowy Village", 0x165a0f11],
]) {
  const structure = await jigsawAssembly({
    assets: classic, folder: "structures", worldgen: classicWorldgen,
    startPool: `minecraft:village/${biome}/town_centers`, depth: 6, radius: 80, seed,
  })
  await writeScene({
    id: `village_${biome}_1161`, name: label, provider: "Java jigsaw pools", version: "1.16.1",
    dimension: "overworld", habitat: biome, structureY: 63, minY: 0, height: 256, seed,
  }, structure)
}
