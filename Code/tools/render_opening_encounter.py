"""Native rendered checks and optional audiovisual capture of the full encounter."""
import argparse,json,os,sys,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
import numpy as np
from ui.opening_scene import OpeningScene
from ui.presentation_renderer import PresentationRenderer


def main():
    args=argparse.ArgumentParser();args.add_argument('--video',action='store_true')
    args.add_argument('--output',type=Path,default=ROOT/'.qa/encounter');options=args.parse_args()
    output=options.output;output.mkdir(parents=True,exist_ok=True)
    pygame.init();pygame.mixer.set_num_channels(32)
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
    screen=pygame.display.set_mode((1920,1080),pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN)
    scene=OpeningScene((1920,1080),None,effects_volume=0);scene.gpu=PresentationRenderer()
    def draw(name=None):
        scene.update(0);scene.render(screen)
        surface=scene.gpu.capture(scene.size) if name else None
        if name:pygame.image.save(surface,output/(name+'.png'))
        scene.gpu.gl.glFinish();pygame.display.flip()
        return surface
    try:
        scene.update(5);draw('shrine')
        scene.place();scene.update(5);draw('shrine-complete')
        scene.activate('door')
        for age in (2,5,9,13,16):
            scene.elapsed=scene.phase_at+age;draw('approach-'+str(age))
        scene.phase='sanctuary';draw('cathedral')
        scene.activate('heart');start=scene.awakened_at
        for age in (0,5,9,12,16,19,24,25.35,25.45,25.65,26.55,27.65,31,34,37,40,43):
            scene.elapsed=start+age;draw('encounter-'+str(age))
        timings=[]
        for frame in range(180):
            scene.elapsed=start+frame/179*43
            before=time.perf_counter();draw();timings.append((time.perf_counter()-before)*1000)
        report={'frames':len(timings),'p50_ms':float(np.percentile(timings,50)),
                'p95_ms':float(np.percentile(timings,95)),'max_ms':max(timings),
                'gl_error':scene.gpu.gl.glGetError(),'renderer':scene.gpu.gl.glGetString(0x1F01).decode()}
        (output/'native-profile.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
        if options.video:
            command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24',
                     '-video_size','1920x1080','-framerate','30','-i','pipe:0',
                     '-i',str(ROOT/'Assets/Sound Hub/opening/encounter.wav'),'-c:v','libx264','-preset','fast',
                     '-crf','19','-c:a','aac','-b:a','192k','-pix_fmt','yuv420p','-movflags','+faststart',
                     '-t','44',str(output/'encounter.mp4')]
            with (output/'video.log').open('wb') as log:
                process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    for frame in range(44*30):
                        pygame.event.pump();scene.elapsed=start+frame/30;scene.update(0);scene.render(screen)
                        process.stdin.write(pygame.image.tobytes(scene.gpu.capture(scene.size),'RGB'))
                        pygame.display.flip()
                    process.stdin.close()
                    if process.wait(timeout=60):raise RuntimeError('ffmpeg failed')
                finally:
                    if process.poll() is None:process.terminate();process.wait(timeout=10)
    finally:scene.close();pygame.quit()


if __name__=='__main__':main()
