"""Release contracts for larger captures and their source-backed presentation."""
import gzip
import hashlib
import json
from pathlib import Path

from engine.biome_capture import ROOT, capture, scene_manifest
from ui.biomes import CURATED_IDS


def test_visible_biomes_are_larger_and_end_pillars_clear_capture_edges():
    for name in CURATED_IDS:
        data=capture(name)
        assert min(data['size'][:2])>=96
    end=capture('the_end')
    assert end['size'][:2]==[256,256]
    pillars=[(x,y) for x,y,z,p in end['blocks'] if end['palette'][p]['Name']=='minecraft:obsidian']
    assert pillars and all(8<x<248 and 8<y<248 for x,y in pillars)


def test_each_new_world_retains_its_complete_natural_landmarks():
    worlds=Path(__file__).resolve().parents[1]/'Code/worlds'
    for name,row in scene_manifest().items():
        if not row.get('world'):continue
        source=capture(name)
        ox,oz=source['origin'][:2];width,depth=source['size'][:2]
        landmarks=[s for s in source['structures'].values() if s.get('id') in source['landmark_ids']]
        assert landmarks
        for landmark in landmarks:
            x0,y0,z0,x1,y1,z1=landmark['BB']
            assert ox<=x0<=x1<ox+width and oz<=z0<=z1<oz+depth
        data=json.loads(gzip.decompress((worlds/(row['world']+'.json.gz')).read_bytes()))
        assert data['scene']['source_capture']==name
        assert data['scene']['origin']==source['origin']
        assert len(data['blocks'])==len(source['blocks'])
        assert not data['scene'].get('decorations')
        assert all(r.get('sourceCapture')==name for r in data['blocks'])
        assert data['bounds']['width']<=512 and data['bounds']['depth']<=512


def test_splash_retains_owner_image_and_native_regular_title():
    import pygame
    from splash import SplashScreen
    from runtime_paths import ICONS_DIR,FONTS_DIR,TEXTURES_DIR
    repo=Path(__file__).resolve().parents[1]
    assert hashlib.sha256((repo/'mariana-salimena-swamp-artstation.jpg').read_bytes()).digest()==hashlib.sha256((Path(ICONS_DIR)/'Splash_Swamp.jpg').read_bytes()).digest()
    pygame.display.init();pygame.font.init()
    try:
        for size in ((960,640),(1200,800),(1920,1080)):
            fitted=SplashScreen.fitted_window_size(*size,ICONS_DIR)
            screen=pygame.display.set_mode(fitted)
            splash=SplashScreen(screen,pygame.time.Clock(),TEXTURES_DIR,FONTS_DIR,ICONS_DIR)
            assert abs(splash.artwork_rect.width/splash.artwork_rect.height-1920/890)<.005
            assert screen.get_rect().contains(splash.artwork_rect)
            assert splash.artwork_rect.contains(splash._title_rect())
            # Integer aspect fitting can leave a single rounding pixel.
            assert max(splash.artwork_rect.topleft)<=1
            assert abs(splash.artwork_rect.width-fitted[0])<=1
            assert abs(splash.artwork_rect.height-fitted[1])<=1
            assert abs(splash.artwork_rect.centerx-fitted[0]//2)<=1
            assert not splash.title_font.get_bold()
            assert splash._title_rect().centerx==fitted[0]//2
            assert splash._title_rect().centery==fitted[1]-24
    finally:
        pygame.display.quit()
