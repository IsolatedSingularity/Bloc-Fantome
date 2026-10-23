"""Matched production panels and complete gallery evidence, with isolated data."""
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Code'))
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
import blocFantome as b


def render(output):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    with patch.object(b, 'APP_CONFIG_FILE', str(output / 'preferences.json')), \
         patch.object(b.BlocFantome, '_saveAppConfig'), patch.object(b.TutorialScreen, '_saveConfig'):
        app = b.BlocFantome(); app.autoSaveEnabled = False; app.tutorialScreen.visible = False
        try:
            assert app.assetManager.loadAllAssets()
            app._createInitialFloor(); app._applyWindowSize(1200, 800)
            app.workshop.visibility.pinned = True
            def capture(name):
                for _ in range(20):
                    app._update(); app._render(); pygame.event.pump()
                    time.sleep(.012)
                pygame.image.save(app.screen, str(output / (name + '.png')))
            for page in ('build', 'world', 'tools', 'menu'):
                app.workshop.page = page; capture(page)
            app.workshop.page = ''; app.settingsMenuOpen = True
            capture('settings'); app.settingsMenuOpen = False
            app._requestExit(); capture('exit'); app._exitAction('stay')
            app.library.open(app); capture('library')
            audit = []
            for tab in ('Worlds', 'Biomes'):
                app.library.change_view(app, tab)
                for dimension in ('overworld', 'nether', 'end'):
                    app.library.dimension = dimension; app.library.refresh(app)
                    for i, entry in enumerate(app.library.entries):
                        preview = app.previewImages.get(app, entry, (280, 180))
                        if preview:
                            name = f"{tab}-{dimension}-{entry['key']}".replace(':', '-')
                            pygame.image.save(preview, str(output / (name + '.png')))
                            audit.append(dict(tab=tab, dimension=dimension, name=entry['name'], image=name+'.png'))
                    app.library.scroll = 0; app.library.scroller.reset()
                    capture(f'{tab}-{dimension}')
            (output / 'gallery.json').write_text(json.dumps(audit, indent=2))
        finally:
            app.worldLoadExecutor.shutdown(wait=True, cancel_futures=True)
            pygame.quit()


if __name__ == '__main__':
    render(sys.argv[1])
