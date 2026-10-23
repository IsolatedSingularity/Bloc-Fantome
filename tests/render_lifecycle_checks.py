"""Production lifecycle frames and silent motion recordings at native sizes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Code'))
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from splash import SplashScreen
from ui.lifecycle import GoodbyeScreen


def render(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('ffmpeg is required for lifecycle motion evidence')
    pygame.init();report=[]
    try:
        for width,height in ((960,640),(1200,800),(1920,1080)):
            screen=pygame.display.set_mode((width,height))
            splash=SplashScreen(screen,pygame.time.Clock(),str(ROOT/'Assets/Texture Hub'),
                                str(ROOT/'Assets/Fonts'),str(ROOT/'Assets/Icons'))
            splash.first_presented_at=1000
            goodbye=GoodbyeScreen(screen,phrase='Leave a little light on.')
            for name,view,seconds in (('splash',splash,4),('goodbye',goodbye,3)):
                path=output/f'{name}-{width}.mp4'
                with (output/f'{name}-{width}-encode.log').open('w') as log:
                    process=subprocess.Popen([ffmpeg,'-y','-f','rawvideo','-pix_fmt','rgb24',
                        '-s',f'{width}x{height}','-r','60','-i','-','-an','-c:v','libx264',
                        '-preset','fast','-crf','18','-pix_fmt','yuv420p',str(path)],
                        stdin=subprocess.PIPE,stdout=log,stderr=log)
                    try:
                        for frame in range(seconds*60):
                            elapsed=frame*1000/60
                            if name=='splash':
                                with patch('pygame.time.get_ticks',return_value=1000+elapsed):view.present()
                            else:view.render(elapsed)
                            if frame in (0,21,41,79,137):
                                pygame.image.save(screen,str(output/f'{name}-{width}-{frame}.png'))
                            process.stdin.write(pygame.image.tobytes(screen,'RGB'))
                    finally:process.stdin.close()
                    if process.wait(timeout=60):raise RuntimeError('Lifecycle recording failed')
                report.append(dict(file=path.name,size=[width,height],fps=60,seconds=seconds,
                                   physical_input=False,audio=False))
            goodbye.reduced=True;goodbye.render(1500)
            pygame.image.save(screen,str(output/f'goodbye-{width}-reduced.png'))
        (output/'recordings.json').write_text(json.dumps(report,indent=2))
    finally:pygame.quit()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    render(parser.parse_args().output)
