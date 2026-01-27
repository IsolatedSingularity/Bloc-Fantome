"""
Horror System Module for Bloc Fantôme

This module manages all horror/ambient features including:
- Cave ambient sounds
- Visual glitches (screen tear, shadow figures)
- Hidden Easter eggs
- Horror rain (black rain with reversed sounds)
- Time-based events (3 AM, Halloween, Friday 13th)
- Progression-based horror intensity

The horror system is designed to be subtle and unsettling rather than
overtly scary. Features are hidden and rare, creating an atmosphere
of unease without disrupting normal gameplay.
"""

import os
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from minecraftBuilder import MinecraftBuilder, AssetManager, World

# Constants
DIMENSION_OVERWORLD = "overworld"
DIMENSION_NETHER = "nether"
DIMENSION_END = "end"


class HorrorManager:
    """
    Manages all horror-related state and behavior.
    
    This class consolidates horror features that were previously scattered
    throughout the main MinecraftBuilder class, making them easier to
    maintain, test, and optionally disable.
    """
    
    def __init__(self, game: 'MinecraftBuilder'):
        """Initialize the horror manager with a reference to the main game."""
        self.game = game
        
        # Master toggle
        self.enabled = True
        
        # Sound state
        self.lastSoundTime = 0
        self.soundMinDelay = 300000  # 5 minutes in ms
        self.soundMaxDelay = 1800000  # 30 minutes in ms
        self.nextSoundTime = random.randint(self.soundMinDelay, self.soundMaxDelay)
        
        # Progression tracking
        self.totalBlocksPlacedAllTime = 0
        self.intensity = 0  # 0-3, increases with blocks placed
        self.sessionPlayTime = 0
        
        # Visual glitch state
        self.visualGlitchChance = 0.0001
        self.lastVisualGlitchTime = 0
        
        # Screen tear
        self.screenTearActive = False
        self.screenTearFrames = 0
        
        # Block flicker
        self.blockFlickerPos: Optional[Tuple[int, int, int]] = None
        self.blockFlickerTimer = 0
        
        # Shadow figure
        self.shadowFigureActive = False
        self.shadowFigurePos: Optional[Tuple[int, int]] = None
        self.shadowFigureFadeTimer = 0
        
        # Ghost cursor
        self.ghostCursorActive = False
        self.ghostCursorPositions: List[Tuple[int, int]] = []
        
        # Block counter glitch
        self.blockCounterGlitch = False
        
        # Subliminal messages
        self.subliminalMessageTimer = 0
        self.subliminalMessage = ""
        
        # Herobrine Easter egg
        self.herobrineActive = False
        self.herobrinePos: Optional[Tuple[int, int]] = None
        self.herobrineFadeTimer = 0
        self.herobrineTriggered = False
        self.herobrineSpotted = 0
        
        # Horror rain state
        self.horrorRainEnabled = False
        self.horrorRainDrops: List[Dict] = []
        self.horrorRainSplashParticles: List[Dict] = []
        self.horrorRainSplashes: List[Dict] = []
        self.horrorLightningBolts: List[List[Tuple[int, int]]] = []
        self.horrorLightningTimer = 0
        self.horrorLightningFlash = 0
        self.nextHorrorLightningTime = 0
        self.horrorRainSound: Optional[pygame.mixer.Sound] = None
        self.horrorRainSoundChannel: Optional[pygame.mixer.Channel] = None
        self.horrorBrightness = 0
        
        # Time-based event flags
        self._3amTriggered = False
        self._halloweenBoost = False
        self._friday13th = False
        
        # Whisper timer (rain whispers)
        self.lastWhisperTime = 0
    
    def update(self, dt: float):
        """
        Update horror system state.
        
        Args:
            dt: Delta time in milliseconds
        """
        if not self.enabled:
            return
        
        currentTime = pygame.time.get_ticks()
        self.sessionPlayTime += dt
        
        # Update horror rain if active
        if self.horrorRainEnabled:
            self._updateHorrorRain(dt)
        
        # Check for ambient horror sounds
        if currentTime >= self.lastSoundTime + self.nextSoundTime:
            self._playRandomSound()
            self.lastSoundTime = currentTime
            self.nextSoundTime = random.randint(self.soundMinDelay, self.soundMaxDelay)
        
        # Update visual effects
        self._updateVisualEffects(dt)
        
        # Update ghost cursor trail
        mouseX, mouseY = pygame.mouse.get_pos()
        self.ghostCursorPositions.append((mouseX, mouseY))
        if len(self.ghostCursorPositions) > 20:
            self.ghostCursorPositions.pop(0)
        
        # Random ghost cursor activation
        if not self.ghostCursorActive and random.random() < 0.0001:
            self.ghostCursorActive = True
        elif self.ghostCursorActive and random.random() < 0.01:
            self.ghostCursorActive = False
        
        # Block counter glitch (very rare)
        if random.random() < 0.00005:
            self.blockCounterGlitch = not self.blockCounterGlitch
        
        # Phantom footsteps
        self._checkPhantomFootsteps()
        
        # Distant knock
        self._checkDistantKnock()
        
        # Breathing sound
        self._checkBreathingSound()
        
        # Subliminal messages
        self._updateSubliminalMessage(dt)
        
        # Update progression intensity
        self._updateIntensity()
        
        # Random visual glitches
        glitchChance = self.visualGlitchChance * (1 + self.intensity * 0.5)
        if random.random() < glitchChance:
            self._triggerRandomVisualGlitch()
        
        # Herobrine check
        self._checkHerobrine(dt)
        
        # Time-based events
        self._checkTimeBasedEvents()
    
    def _updateVisualEffects(self, dt: float):
        """Update timers for active visual effects."""
        if self.screenTearActive:
            self.screenTearFrames -= 1
            if self.screenTearFrames <= 0:
                self.screenTearActive = False
        
        if self.blockFlickerPos:
            self.blockFlickerTimer -= dt
            if self.blockFlickerTimer <= 0:
                self.blockFlickerPos = None
        
        if self.shadowFigureActive:
            self.shadowFigureFadeTimer -= dt
            if self.shadowFigureFadeTimer <= 0:
                self.shadowFigureActive = False
                self.shadowFigurePos = None
    
    def _checkPhantomFootsteps(self):
        """Check for phantom footstep sound trigger."""
        assetMgr = self.game.assetManager
        if hasattr(assetMgr, 'phantomFootsteps') and assetMgr.phantomFootsteps:
            if random.random() < 0.000005 * (1 + self.intensity * 0.3):
                sound = random.choice(assetMgr.phantomFootsteps)
                sound.play()
    
    def _checkDistantKnock(self):
        """Check for distant knock sound trigger."""
        assetMgr = self.game.assetManager
        if hasattr(assetMgr, 'knockSound') and assetMgr.knockSound:
            if random.random() < 0.000002 * (1 + self.intensity * 0.2):
                assetMgr.knockSound.play()
    
    def _checkBreathingSound(self):
        """Check for breathing sound trigger."""
        assetMgr = self.game.assetManager
        if hasattr(assetMgr, 'breathSound') and assetMgr.breathSound:
            if random.random() < 0.000001 * (1 + self.intensity * 0.3):
                assetMgr.breathSound.play()
    
    def _updateSubliminalMessage(self, dt: float):
        """Update subliminal message timer."""
        if self.subliminalMessageTimer > 0:
            self.subliminalMessageTimer -= dt
        elif random.random() < 0.00001:
            self.subliminalMessage = random.choice([
                "WATCHING", "IT SEES", "NOT ALONE", "BEHIND YOU", "WE WAIT"
            ])
            self.subliminalMessageTimer = 16  # ~1 frame
    
    def _updateIntensity(self):
        """Update horror intensity based on total blocks placed."""
        totalBlocks = self.game.blocksPlaced + self.totalBlocksPlacedAllTime
        if totalBlocks >= 10000:
            self.intensity = 3
        elif totalBlocks >= 5000:
            self.intensity = 2
        elif totalBlocks >= 1000:
            self.intensity = 1
        else:
            self.intensity = 0
    
    def _checkHerobrine(self, dt: float):
        """Check for Herobrine Easter egg trigger."""
        if self.herobrineFadeTimer > 0:
            self.herobrineFadeTimer -= dt
            if self.herobrineFadeTimer <= 0:
                self.herobrineActive = False
                self.herobrinePos = None
        elif self.sessionPlayTime >= 1800000:  # 30 minutes
            if random.random() < 0.000001 * (1 + self.herobrineSpotted * 0.5):
                self._triggerHerobrine()
    
    def _triggerHerobrine(self):
        """Trigger a Herobrine sighting at the edge of the screen."""
        if self.herobrineActive:
            return
        
        self.herobrineActive = True
        self.herobrineTriggered = True
        self.herobrineSpotted += 1
        
        windowWidth = self.game.screen.get_width()
        windowHeight = self.game.screen.get_height()
        panelWidth = getattr(self.game, 'panelWidth', 300)
        
        edge = random.choice(["left", "right", "top"])
        if edge == "left":
            self.herobrinePos = (30, random.randint(200, windowHeight - 200))
        elif edge == "right":
            self.herobrinePos = (windowWidth - panelWidth - 50, random.randint(200, windowHeight - 200))
        else:
            self.herobrinePos = (random.randint(100, windowWidth - panelWidth - 100), 50)
        
        self.herobrineFadeTimer = 150  # ~2.5 seconds
    
    def _checkTimeBasedEvents(self):
        """Check for time-based horror events."""
        now = datetime.now()
        
        # 3:00 AM event
        if now.hour == 3 and now.minute == 0 and now.second < 5:
            if not self._3amTriggered:
                self._3amTriggered = True
                self.screenTearActive = True
                self.screenTearFrames = 10
                pygame.mixer.music.pause()
                pygame.time.set_timer(pygame.USEREVENT + 10, 3000, loops=1)
        elif now.hour != 3 or now.minute != 0:
            self._3amTriggered = False
        
        # Halloween
        if now.month == 10 and now.day == 31:
            if not self._halloweenBoost:
                self._halloweenBoost = True
                self.soundMinDelay = 150000
                self.soundMaxDelay = 600000
        else:
            if self._halloweenBoost:
                self._halloweenBoost = False
                self.soundMinDelay = 300000
                self.soundMaxDelay = 1800000
        
        # Friday the 13th
        self._friday13th = (now.weekday() == 4 and now.day == 13)
    
    def _triggerRandomVisualGlitch(self):
        """Trigger a random visual glitch effect."""
        glitchType = random.choice(["screen_tear", "block_flicker", "shadow_figure"])
        
        if glitchType == "screen_tear":
            self.screenTearActive = True
            self.screenTearFrames = random.randint(1, 3)
        
        elif glitchType == "block_flicker" and self.game.world.blocks:
            positions = list(self.game.world.blocks.keys())
            self.blockFlickerPos = random.choice(positions)
            self.blockFlickerTimer = 16
        
        elif glitchType == "shadow_figure":
            self.shadowFigureActive = True
            windowWidth = self.game.screen.get_width()
            windowHeight = self.game.screen.get_height()
            panelWidth = getattr(self.game, 'panelWidth', 300)
            
            edge = random.choice(["left", "right"])
            if edge == "left":
                self.shadowFigurePos = (20, random.randint(100, windowHeight - 200))
            else:
                self.shadowFigurePos = (windowWidth - panelWidth - 50, random.randint(100, windowHeight - 200))
            self.shadowFigureFadeTimer = 150
    
    def _playRandomSound(self):
        """Play a random horror ambient sound based on current dimension."""
        assetMgr = self.game.assetManager
        dimension = self.game.currentDimension
        sounds = []
        
        if dimension == DIMENSION_NETHER:
            if hasattr(assetMgr, 'netherAmbientSounds') and assetMgr.netherAmbientSounds:
                sounds = assetMgr.netherAmbientSounds
            if hasattr(assetMgr, 'ghastMoans') and assetMgr.ghastMoans:
                if random.random() < 0.15:
                    ghast = random.choice(assetMgr.ghastMoans)
                    ghast.play()
        elif dimension == DIMENSION_END:
            if hasattr(assetMgr, 'endermanSounds') and assetMgr.endermanSounds:
                if random.random() < 0.3:
                    enderman = random.choice(assetMgr.endermanSounds)
                    enderman.play()
            if hasattr(assetMgr, 'caveSounds') and assetMgr.caveSounds:
                sounds = assetMgr.caveSounds
        else:
            if hasattr(assetMgr, 'caveSounds') and assetMgr.caveSounds:
                sounds = assetMgr.caveSounds
        
        if sounds:
            sound = random.choice(sounds)
            sound.play()
    
    # ========================
    # HORROR RAIN SYSTEM
    # ========================
    
    def toggleHorrorRain(self):
        """Toggle horror rain on/off."""
        # Stop normal weather if active
        if hasattr(self.game, 'rainEnabled') and self.game.rainEnabled:
            self.game.rainEnabled = False
            if hasattr(self.game, '_stopRain'):
                self.game._stopRain()
        if hasattr(self.game, 'snowEnabled') and self.game.snowEnabled:
            self.game.snowEnabled = False
            if hasattr(self.game, '_stopSnow'):
                self.game._stopSnow()
        
        self.horrorRainEnabled = not self.horrorRainEnabled
        
        if self.horrorRainEnabled:
            self._startHorrorRain()
        else:
            self._stopHorrorRain()
    
    def _startHorrorRain(self):
        """Initialize horror rain effects."""
        windowWidth = self.game.screen.get_width()
        windowHeight = self.game.screen.get_height()
        
        self.horrorRainDrops = []
        self.game.skyDarkness = 180
        self.horrorLightningBolts = []
        self.horrorLightningTimer = 0
        self.horrorLightningFlash = 0
        self.nextHorrorLightningTime = random.randint(5000, 12000)
        self.horrorBrightness = 100
        
        # Create initial rain drops
        for _ in range(200):
            self.horrorRainDrops.append({
                "x": random.randint(0, windowWidth),
                "y": random.randint(-windowHeight, 0),
                "speed": random.randint(8, 15),
                "length": random.randint(15, 30),
                "angle": random.uniform(-0.05, 0.05)
            })
        
        # Create distorted rain sound
        self._createHorrorRainSound()
        
        # Play the horror rain sound
        if self.horrorRainSound:
            try:
                self.horrorRainSoundChannel = self.horrorRainSound.play(loops=-1)
            except Exception as e:
                print(f"Could not play horror rain sound: {e}")
    
    def _createHorrorRainSound(self):
        """Create the distorted horror rain sound from normal rain."""
        assetMgr = self.game.assetManager
        if hasattr(assetMgr, 'relaxingRainSound') and assetMgr.relaxingRainSound and not self.horrorRainSound:
            try:
                import numpy as np
                soundArray = pygame.sndarray.array(assetMgr.relaxingRainSound)
                pitchedDown = np.repeat(soundArray[::2], 2, axis=0)[:len(soundArray)]
                bitcrushed = (pitchedDown // 512) * 512
                length = len(bitcrushed)
                warble = np.sin(np.linspace(0, 30 * np.pi, length)).reshape(-1, 1) * 3000
                warbled = np.clip(bitcrushed.astype(np.float32) + warble, -32768, 32767)
                noise = np.random.randint(-800, 800, warbled.shape, dtype=np.int16)
                distorted = np.clip(warbled.astype(np.int32) + noise, -32768, 32767)
                self.horrorRainSound = pygame.sndarray.make_sound(distorted.astype(np.int16))
                self.horrorRainSound.set_volume(0.5)
            except ImportError:
                # numpy not available - use regular rain sound at lower volume as fallback
                self.horrorRainSound = assetMgr.relaxingRainSound
                if self.horrorRainSound:
                    self.horrorRainSound.set_volume(0.3)
            except Exception as e:
                print(f"Could not create horror rain sound: {e}")
                # Fallback to regular rain sound
                self.horrorRainSound = assetMgr.relaxingRainSound
                if self.horrorRainSound:
                    self.horrorRainSound.set_volume(0.3)
    
    def _stopHorrorRain(self):
        """Stop horror rain effects."""
        self.horrorRainDrops = []
        self.horrorRainSplashParticles = []
        self.horrorRainSplashes = []
        self.game.skyDarkness = 0
        self.horrorBrightness = 0
        self.horrorLightningBolts = []
        self.horrorLightningFlash = 0
        
        if self.horrorRainSoundChannel:
            self.horrorRainSoundChannel.stop()
            self.horrorRainSoundChannel = None
    
    def _updateHorrorRain(self, dt: int):
        """Update horror rain animation."""
        windowWidth = self.game.screen.get_width()
        windowHeight = self.game.screen.get_height()
        panelWidth = getattr(self.game, 'panelWidth', 300)
        panelLeft = windowWidth - panelWidth
        dtSec = dt / 1000.0
        
        # Update rain drops
        for drop in self.horrorRainDrops:
            drop["y"] += drop["speed"]
            drop["x"] += drop["angle"] * drop["speed"]
            if drop["y"] > windowHeight:
                drop["y"] = random.randint(-50, 0)
                drop["x"] = random.randint(0, windowWidth)
        
        # Spawn splashes on blocks
        self._spawnHorrorSplashesOnBlocks()
        
        # Update 2D splashes
        for splash in self.horrorRainSplashes:
            splash["life"] -= 1
        self.horrorRainSplashes = [s for s in self.horrorRainSplashes if s["life"] > 0]
        
        # Update 3D splash particles
        gravity = 0.2
        for particle in self.horrorRainSplashParticles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += gravity
            particle["life"] -= dtSec / particle["maxLife"]
        self.horrorRainSplashParticles = [p for p in self.horrorRainSplashParticles if p["life"] > 0]
        
        # Lightning timing
        self.horrorLightningTimer += dt
        if self.horrorLightningTimer >= self.nextHorrorLightningTime:
            if random.random() < 0.6:
                self._triggerHorrorLightning()
            self.horrorLightningTimer = 0
            self.nextHorrorLightningTime = random.randint(4000, 10000)
        
        # Fade lightning flash
        if self.horrorLightningFlash > 0:
            self.horrorLightningFlash = max(0, self.horrorLightningFlash - 5)
        
        # Clear lightning bolts when flash is gone
        if self.horrorLightningFlash <= 0:
            self.horrorLightningBolts = []
    
    def _spawnHorrorSplashesOnBlocks(self):
        """Spawn horror splash effects on random blocks."""
        world = self.game.world
        renderer = self.game.renderer
        
        topBlocks = {}
        for (x, y, z), blockType in world.blocks.items():
            if (x, y) not in topBlocks or z > topBlocks[(x, y)]:
                topBlocks[(x, y)] = z
        
        if not topBlocks:
            return
        
        blockList = list(topBlocks.items())
        numSplashes = min(len(blockList), random.randint(3, 5))
        
        tileHeight = getattr(self.game, 'TILE_HEIGHT', 16)
        panOffsetX = getattr(self.game, 'panOffsetX', 0)
        panOffsetY = getattr(self.game, 'panOffsetY', 0)
        
        for _ in range(numSplashes):
            (x, y), z = random.choice(blockList)
            screenX, screenY = renderer.worldToScreen(x, y, z)
            
            offsetX = random.randint(-6, 6)
            offsetY = random.randint(-3, 3)
            splashX = screenX + panOffsetX + offsetX
            splashY = screenY + panOffsetY + tileHeight // 4 + offsetY
            
            self.horrorRainSplashes.append({
                "x": splashX,
                "y": splashY,
                "life": 12,
                "size": random.randint(2, 5)
            })
            
            if random.random() < 0.3:
                self._spawnHorrorSplash(splashX, splashY)
    
    def _spawnHorrorSplash(self, x: float, y: float):
        """Spawn 3D splash particles for horror rain."""
        colors = [(10, 5, 15), (20, 10, 25), (5, 0, 10), (30, 15, 35), (15, 5, 20)]
        numParticles = random.randint(8, 12)
        
        for _ in range(numParticles):
            self.horrorRainSplashParticles.append({
                "x": x + random.randint(-8, 8),
                "y": y + random.randint(-5, 5),
                "vx": random.uniform(-3, 3),
                "vy": random.uniform(-4, -1),
                "color": random.choice(colors),
                "life": 1.0,
                "maxLife": random.uniform(0.4, 0.8),
                "size": random.randint(3, 6)
            })
    
    def _triggerHorrorLightning(self):
        """Trigger red lightning bolts with horror sound."""
        windowWidth = self.game.screen.get_width()
        windowHeight = self.game.screen.get_height()
        panelWidth = getattr(self.game, 'panelWidth', 300)
        panelLeft = windowWidth - panelWidth
        
        self.horrorLightningBolts = []
        self.horrorLightningFlash = 150
        
        for _ in range(3):
            bolt = []
            startX = random.randint(50, panelLeft - 50)
            startY = 0
            endX = startX + random.randint(-150, 150)
            endX = max(50, min(panelLeft - 50, endX))
            endY = random.randint(windowHeight // 2, windowHeight - 50)
            
            bolt.append((startX, startY))
            currentX, currentY = startX, startY
            
            while currentY < endY - 20:
                currentY += random.randint(30, 60)
                directionBias = (endX - currentX) * 0.15
                currentX += random.randint(-40, 40) + int(directionBias)
                currentX = max(50, min(panelLeft - 50, currentX))
                bolt.append((currentX, min(currentY, endY)))
            
            self.horrorLightningBolts.append(bolt)
        
        # Play thunder
        assetMgr = self.game.assetManager
        if hasattr(assetMgr, 'thunderSounds') and assetMgr.thunderSounds:
            thunderSound = random.choice(assetMgr.thunderSounds)
            for i in range(3):
                channel = pygame.mixer.find_channel()
                if channel:
                    channel.play(thunderSound)
                    channel.set_volume(1.0)
    
    # ========================
    # RENDERING
    # ========================
    
    def render(self, screen: pygame.Surface):
        """Render all horror visual effects."""
        if not self.enabled:
            return
        
        windowWidth = screen.get_width()
        windowHeight = screen.get_height()
        panelWidth = getattr(self.game, 'panelWidth', 300)
        
        # Render horror rain if active
        if self.horrorRainEnabled:
            self._renderHorrorRain(screen)
        
        # Progression-based darkening
        if self.intensity > 0:
            darkenAlpha = self.intensity * 5
            darkenOverlay = pygame.Surface((windowWidth, windowHeight), pygame.SRCALPHA)
            darkenOverlay.fill((0, 0, 0, darkenAlpha))
            screen.blit(darkenOverlay, (0, 0))
        
        # Screen tear effect
        if self.screenTearActive:
            tearY = random.randint(50, windowHeight - 100)
            tearHeight = random.randint(2, 8)
            displacement = random.choice([-3, -2, -1, 1, 2, 3])
            try:
                strip = screen.subsurface((0, tearY, windowWidth, tearHeight)).copy()
                screen.blit(strip, (displacement, tearY))
            except ValueError:
                pass
        
        # Shadow figure
        if self.shadowFigureActive and self.shadowFigurePos:
            self._renderShadowFigure(screen)
        
        # Ghost cursor
        if self.ghostCursorActive and len(self.ghostCursorPositions) > 3:
            self._renderGhostCursor(screen)
        
        # Subliminal message
        if self.subliminalMessageTimer > 0 and self.subliminalMessage:
            self._renderSubliminalMessage(screen)
        
        # Herobrine
        if self.herobrineActive and self.herobrinePos:
            self._renderHerobrine(screen)
        
        # Random red pixel
        if random.random() < 0.0001:
            panelLeft = windowWidth - panelWidth
            redX = random.randint(100, panelLeft - 100)
            redY = random.randint(100, windowHeight - 100)
            screen.set_at((redX, redY), (255, 0, 0))
        
        # Hidden Nether eyes
        if self.game.currentDimension == DIMENSION_NETHER and random.random() < 0.0003:
            self._renderHiddenNetherEyes(screen)
    
    def _renderShadowFigure(self, screen: pygame.Surface):
        """Render the shadow figure effect."""
        figX, figY = self.shadowFigurePos
        figWidth, figHeight = 20, 60
        alpha = max(5, min(25, int(self.shadowFigureFadeTimer / 6)))
        
        figureSurf = pygame.Surface((figWidth, figHeight), pygame.SRCALPHA)
        pygame.draw.ellipse(figureSurf, (10, 10, 15, alpha), (5, 0, 10, 12))  # Head
        pygame.draw.rect(figureSurf, (10, 10, 15, alpha), (6, 12, 8, 25))  # Body
        pygame.draw.rect(figureSurf, (10, 10, 15, alpha), (6, 37, 3, 20))  # Left leg
        pygame.draw.rect(figureSurf, (10, 10, 15, alpha), (11, 37, 3, 20))  # Right leg
        screen.blit(figureSurf, (figX, figY))
    
    def _renderGhostCursor(self, screen: pygame.Surface):
        """Render the ghost cursor trail."""
        for i, (gx, gy) in enumerate(self.ghostCursorPositions[:-1]):
            alpha = int((i / len(self.ghostCursorPositions)) * 15) + 3
            ghostSurf = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(ghostSurf, (100, 100, 120, alpha), (4, 4), 4)
            screen.blit(ghostSurf, (gx - 4, gy - 4))
    
    def _renderSubliminalMessage(self, screen: pygame.Surface):
        """Render a subliminal message in a corner."""
        windowWidth = screen.get_width()
        windowHeight = screen.get_height()
        
        font = getattr(self.game, 'smallFont', None)
        if font:
            msgSurf = font.render(self.subliminalMessage, True, (80, 0, 0))
            msgSurf.set_alpha(30)
            corner = random.choice([
                (10, 10), (windowWidth - 100, 10),
                (10, windowHeight - 30), (windowWidth - 100, windowHeight - 30)
            ])
            screen.blit(msgSurf, corner)
    
    def _renderHerobrine(self, screen: pygame.Surface):
        """Render the Herobrine Easter egg."""
        hbX, hbY = self.herobrinePos
        
        if self.herobrineFadeTimer > 100:
            alpha = min(40, int((150 - self.herobrineFadeTimer) * 0.8))
        else:
            alpha = min(40, int(self.herobrineFadeTimer * 0.4))
        
        hbWidth, hbHeight = 12, 28
        hbSurf = pygame.Surface((hbWidth, hbHeight), pygame.SRCALPHA)
        
        # Head
        pygame.draw.rect(hbSurf, (230, 230, 230, alpha), (2, 0, 8, 8))
        # Eyes
        eyeAlpha = min(80, alpha * 2)
        pygame.draw.rect(hbSurf, (255, 255, 255, eyeAlpha), (3, 2, 2, 2))
        pygame.draw.rect(hbSurf, (255, 255, 255, eyeAlpha), (7, 2, 2, 2))
        # Body
        pygame.draw.rect(hbSurf, (0, 170, 170, alpha), (2, 8, 8, 10))
        # Legs
        pygame.draw.rect(hbSurf, (30, 30, 100, alpha), (2, 18, 3, 10))
        pygame.draw.rect(hbSurf, (30, 30, 100, alpha), (7, 18, 3, 10))
        
        screen.blit(hbSurf, (hbX, hbY))
        
        # Despawn if cursor gets close
        mouseX, mouseY = pygame.mouse.get_pos()
        distToHB = ((mouseX - hbX) ** 2 + (mouseY - hbY) ** 2) ** 0.5
        if distToHB < 150:
            self.herobrineActive = False
            self.herobrinePos = None
    
    def _renderHiddenNetherEyes(self, screen: pygame.Surface):
        """Render barely-visible eyes in the Nether."""
        windowWidth = screen.get_width()
        windowHeight = screen.get_height()
        panelWidth = getattr(self.game, 'panelWidth', 300)
        panelLeft = windowWidth - panelWidth
        
        eyeX = random.randint(50, panelLeft - 50)
        eyeY = random.randint(100, windowHeight - 100)
        eyeAlpha = random.randint(8, 18)
        
        eyeSurf = pygame.Surface((16, 8), pygame.SRCALPHA)
        pygame.draw.circle(eyeSurf, (200, 50, 50, eyeAlpha), (4, 4), 3)
        pygame.draw.circle(eyeSurf, (200, 50, 50, eyeAlpha), (12, 4), 3)
        screen.blit(eyeSurf, (eyeX, eyeY))
    
    def _renderHorrorRain(self, screen: pygame.Surface):
        """Render horror rain effects."""
        windowWidth = screen.get_width()
        windowHeight = screen.get_height()
        panelWidth = getattr(self.game, 'panelWidth', 300)
        panelLeft = windowWidth - panelWidth
        
        # Render fog
        self._renderHorrorFog(screen)
        
        # Rain drops
        for drop in self.horrorRainDrops:
            if drop["x"] > panelLeft:
                continue
            endX = drop["x"] + drop["angle"] * drop["length"]
            endY = drop["y"] + drop["length"]
            
            # Glow
            glowColor = (40, 80, 140, 30)
            glowSurf = pygame.Surface((8, int(drop["length"]) + 4), pygame.SRCALPHA)
            pygame.draw.line(glowSurf, glowColor, (4, 0), (4, int(drop["length"])), 6)
            screen.blit(glowSurf, (int(drop["x"]) - 4, int(drop["y"]) - 2))
            
            # Core
            rainColor = (15, 10, 25)
            pygame.draw.line(screen, rainColor,
                           (int(drop["x"]), int(drop["y"])),
                           (int(endX), int(endY)), 2)
        
        # 3D splash particles
        for particle in self.horrorRainSplashParticles:
            if particle["x"] > panelLeft:
                continue
            alpha = int(particle["life"] * 255)
            color = (*particle["color"], alpha)
            size = max(2, int(particle["size"] * (0.5 + particle["life"] * 0.5)))
            if size > 0:
                particleSurf = pygame.Surface((size, size), pygame.SRCALPHA)
                particleSurf.fill(color)
                if size > 2:
                    darker = (max(0, particle["color"][0] - 5),
                             max(0, particle["color"][1] - 5),
                             max(0, particle["color"][2] - 5), alpha)
                    pygame.draw.rect(particleSurf, darker, (0, 0, size, size), 1)
                screen.blit(particleSurf, (int(particle["x"]), int(particle["y"])))
        
        # 2D splash effects
        for splash in self.horrorRainSplashes:
            if splash["x"] > panelLeft:
                continue
            alpha = int(180 * (splash["life"] / 12))
            expansion = (12 - splash["life"]) * 0.5
            size = splash["size"] + expansion
            
            splashSurf = pygame.Surface((int(size * 3), int(size * 1.5)), pygame.SRCALPHA)
            splashColor = (40, 20, 60, alpha)
            pygame.draw.ellipse(splashSurf, splashColor, splashSurf.get_rect(), 2)
            screen.blit(splashSurf, (splash["x"] - size * 1.5, splash["y"] - size * 0.75))
            
            if splash["life"] > 6:
                dotSize = max(2, splash["size"] - 1)
                dotSurf = pygame.Surface((dotSize * 2, dotSize), pygame.SRCALPHA)
                dotColor = (20, 10, 30, alpha)
                pygame.draw.ellipse(dotSurf, dotColor, dotSurf.get_rect())
                screen.blit(dotSurf, (splash["x"] - dotSize, splash["y"] - dotSize // 2))
        
        # Lightning bolts
        for bolt in self.horrorLightningBolts:
            if len(bolt) >= 2:
                for i in range(len(bolt) - 1):
                    start, end = bolt[i], bolt[i + 1]
                    pygame.draw.line(screen, (100, 0, 0), start, end, 9)
                    pygame.draw.line(screen, (150, 0, 0), start, end, 6)
                    pygame.draw.line(screen, (255, 50, 50), start, end, 3)
                    pygame.draw.line(screen, (255, 100, 100), start, end, 2)
        
        # Lightning flash overlay
        if self.horrorLightningFlash > 0:
            flashOverlay = pygame.Surface((panelLeft, windowHeight), pygame.SRCALPHA)
            flashOverlay.fill((255, 0, 0, min(100, self.horrorLightningFlash)))
            screen.blit(flashOverlay, (0, 0))
    
    def _renderHorrorFog(self, screen: pygame.Surface):
        """Render fog during horror rain."""
        # This is a simplified fog - the full implementation requires
        # access to the world grid and renderer which is complex to extract.
        # For now, this is a placeholder that can be enhanced later.
        pass
    
    # ========================
    # SERIALIZATION
    # ========================
    
    def getState(self) -> Dict:
        """Get serializable state for saving."""
        return {
            "totalBlocksPlacedAllTime": self.totalBlocksPlacedAllTime,
            "herobrineSpotted": self.herobrineSpotted,
            "intensity": self.intensity
        }
    
    def setState(self, state: Dict):
        """Restore state from save data."""
        self.totalBlocksPlacedAllTime = state.get("totalBlocksPlacedAllTime", 0)
        self.herobrineSpotted = state.get("herobrineSpotted", 0)
        self.intensity = state.get("intensity", 0)
