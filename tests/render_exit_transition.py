"""Reproduce the old early-Escape painting leak using its exact committed method."""
import ast
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Code'))
import pygame
import blocFantome as module
from splash import SplashScreen


def render(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    baseline='d5359724e0d7e380e5bc01cf527f46da55bfdcc3'
    source=subprocess.check_output(['git','show',baseline+':Code/blocFantome.py']).decode('utf-8')
    cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='BlocFantome')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_requestExit')
    namespace={};exec(compile(ast.Module(body=[method],type_ignores=[]),'<baseline _requestExit>','exec'),namespace)
    with patch.object(module,'APP_CONFIG_FILE',str(out/'isolated.json')),patch.object(module.BlocFantome,'_saveAppConfig'):
        app=module.BlocFantome();app.autoSaveEnabled=False
        try:
            assert app.assetManager.loadAllAssets();app._createInitialFloor()
            app.tutorialScreen.visible=False
            for name,request in (('before',namespace['_requestExit']),('after',module.BlocFantome._requestExit)):
                app._exitDialog=None
                splash=SplashScreen(app.screen,app.clock,module.TEXTURES_DIR,module.FONTS_DIR,module.ICONS_DIR)
                app._startupOverlay=splash.background_tile.copy()
                app._startupOverlay.blit(splash.title,splash._title_rect())
                app._startupRevealStarted=None
                app._render()  # Actual first editor frame, still under its boot overlay.
                request(app);app._render()
                pygame.image.save(app.screen,str(out/(name+'.png')))
            (out/'report.json').write_text(json.dumps(dict(baseline=baseline,
                reproduced='Early Escape during the 220 ms boot-to-editor reveal captures and re-presents the swamp artwork and its dark margins in exit confirmation.',
                limitation='The owner-specific full exit sequence is not independently recorded; this is a reproduced transition defect, not a claim that it was the only cause.'),indent=2),encoding='utf-8')
        finally:app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()


if __name__=='__main__':render(sys.argv[1])
