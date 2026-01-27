# Assets Directory

This directory contains the visual and audio assets for Bloc Fantôme.

**⚠️ IMPORTANT:** The `Texture Hub/` and `Sound Hub/` folders are NOT included in this repository. You must run the setup script to extract assets from your own Minecraft installation.

## 🔧 Setup Instructions

```bash
cd Code
python setup_assets.py
```

This script will extract textures and sounds from your local Minecraft Java Edition installation (version 1.21.1 or later required).

## 📂 Directory Structure

```
Assets/
├── Extensive Library/    # Additional data files (included)
│   ├── assets/          # Block states, models, particles
│   ├── dimension_type/  # Dimension configuration JSONs
│   ├── structures/      # NBT structure templates
│   ├── textures/        # Extended texture library
│   └── worldgen/        # World generation configs
│
├── Fonts/               # Custom fonts (included)
│   └── Agreement.txt    # Font license agreement
│
├── Icons/               # Application icons (included)
│   └── End_Stone.ico    # Main app icon
│
├── Sound Hub/           # Audio files (NOT INCLUDED - run setup_assets.py)
│   ├── ambient/         # Environmental sounds
│   ├── block/           # Block sounds
│   ├── dig/             # Digging sounds
│   ├── music/           # Background music
│   └── ...
│
├── Texture Hub/         # Visual textures (NOT INCLUDED - run setup_assets.py)
│   ├── blocks/          # Block face textures
│   ├── gui/             # UI elements
│   ├── entity/          # Entity textures
│   └── ...
│
└── Extras/              # Archive of additional assets
```

## ⚠️ Legal Notice

> **DISCLAIMER:** This is an unofficial fan project and is **NOT** affiliated with, 
> endorsed by, or connected to Mojang Studios or Microsoft.
>
> Users must own a legitimate copy of Minecraft Java Edition to use this application.
> The setup script extracts assets from the user's own legal installation.
>
> Minecraft® is a registered trademark of Mojang Synergies AB.
