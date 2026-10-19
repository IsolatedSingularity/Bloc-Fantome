import os,sys,subprocess,shutil,time,json
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
sys.path.insert(0,str(Path.cwd()/'Code'))
import pygame
from blocFantome import BlocFantome
from ui.opening_scene import OpeningScene,MUSIC_PATH
app=BlocFantome();app.assetManager.loadAllAssets()
scene=OpeningScene((1200,800),app.assetManager)
out=Path('.qa/opening-294/opening-preview.mp4')
process=subprocess.Popen([shutil.which('ffmpeg'),'-y','-hide_banner','-loglevel','error',
    '-f','rawvideo','-pixel_format','rgb24','-video_size','1200x800','-framerate','60',
    '-i','pipe:0','-i',MUSIC_PATH,'-t','12','-c:v','libx264','-preset','fast','-crf','20',
    '-pix_fmt','yuv420p','-c:a','aac','-af','volume=0.32','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
try:
    for frame in range(720):
        if frame==300:assert scene.place()
        if frame==270:
            x,y=scene.renderer.worldToScreen(*scene.TARGET)
            scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION,pos=(x,y+20)))
        scene.render(app.screen)
        process.stdin.write(pygame.image.tobytes(app.screen,'RGB'))
        scene.update(1/60)
finally:
    process.stdin.close()
    assert process.wait()==0
    app.worldLoadExecutor.shutdown(wait=True);pygame.quit()
print(out)
