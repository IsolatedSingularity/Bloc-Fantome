# Assets Directory

This directory contains all visual and audio assets for Bite Sized Minecraft.

## 📂 Directory Structure

```
Assets/
├── Extensive Library/    # Additional Minecraft data files
│   ├── assets/          # Block states, models, particles
│   ├── dimension_type/  # Dimension configuration JSONs
│   ├── structures/      # NBT structure templates
│   ├── textures/        # Extended texture library
│   └── worldgen/        # World generation configs
│
├── Fonts/               # Custom fonts
│   └── Agreement.txt    # Font license agreement
│
├── Icons/               # Application icons
│   └── End_Stone.ico    # Main app icon (isometric end stone)
│
├── Sound Hub/           # Audio files
│   ├── ambient/         # Environmental sounds (cave, nether, weather)
│   ├── block/           # Block placement/breaking sounds
│   ├── damage/          # Damage sounds
│   ├── dig/             # Digging sounds
│   ├── enchant/         # Enchantment sounds
│   ├── entity/          # Entity sounds
│   ├── fire/            # Fire sounds
│   ├── liquid/          # Water and lava sounds
│   ├── mob/             # Mob sounds
│   ├── music/           # Background music
│   ├── portal/          # Portal sounds
│   ├── random/          # Miscellaneous sounds
│   ├── records/         # Music disc tracks
│   ├── step/            # Footstep sounds
│   └── ui/              # UI interaction sounds
│
├── Texture Hub/         # Visual textures
│   ├── blocks/          # 32x32 block face textures (upscaled from 16x16)
│   ├── colormap/        # Biome color maps
│   ├── effect/          # Visual effects
│   ├── entity/          # Entity textures (chests, etc.)
│   ├── environment/     # Sky, clouds, etc.
│   ├── font/            # Bitmap fonts
│   ├── gui/             # UI elements (buttons, slots, etc.)
│   ├── items/           # Item textures
│   ├── misc/            # Miscellaneous textures
│   ├── painting/        # Painting textures
│   └── particle/        # Particle effect textures
│
└── Extras/              # Archive of additional/unused assets
    ├── fossil/          # Fossil structure templates
    ├── shipwreck/       # Shipwreck templates
    └── ...
```

## 📜 Asset Sources & Licensing

### Minecraft Textures & Sounds
- **Source:** [Official Minecraft Resource Pack Template](https://aka.ms/resourcepacktemplate)
- **Copyright:** © Mojang Studios / Microsoft
- **Usage:** Educational and non-commercial fan project only
- **Note:** These assets are NOT included in this repository and must be downloaded separately

### Block Textures (Texture Hub/blocks/)
All block textures are sourced from the official Mojang resource pack and upscaled from 16x16 to 32x32 using nearest-neighbor interpolation to maintain pixel-art aesthetics.

### Sound Effects (Sound Hub/)
Sound effects are from the official Minecraft resource pack:
- Block sounds (dig, step, place)
- Ambient sounds (cave, nether, underwater)
- Music tracks
- UI sounds

### Fonts (Fonts/)
Custom fonts are used under their respective licenses. See `Fonts/Agreement.txt` for details.

### Custom Assets
The following assets were created specifically for this project:
- `Icons/End_Stone.ico` - Application icon (derived from end_stone texture)
- UI layout and arrangement

## ⚠️ Legal Notice

> **DISCLAIMER:** This is an unofficial fan project and is **NOT** affiliated with, 
> endorsed by, or connected to Mojang Studios or Microsoft. 
> 
> All Minecraft-related textures, sounds, and other assets remain the property of 
> Mojang Studios / Microsoft and are used here for educational and non-commercial 
> purposes only under fair use principles.
>
> Minecraft® is a registered trademark of Mojang Synergies AB.

## 🔧 Asset Management

### Downloading Assets
If assets are missing, run the asset downloader:
```bash
cd Code
python downloadAssets.py
```

### Texture Format
- Block textures: 32x32 PNG with alpha channel
- UI elements: Various sizes, PNG format
- All textures should use nearest-neighbor scaling to preserve pixel art

### Sound Format
- Format: OGG Vorbis (.ogg)
- Sample rate: 44100 Hz
- Channels: Mono or Stereo
