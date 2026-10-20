"""Render the isolated, silent motion checkpoint with the real Windows renderer.

Run with Python 3.12: Code/tools/render_creature_proof.py [--video] [--preview]
No live game, saves, preferences, audio devices or release files are touched.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
import numpy as np
import pygame
from ui.opening_creature import DURATION, sample, body_mesh
from ui.opening_geometry import sanctuary, distant_arches
from ui.presentation_renderer import Camera, PresentationRenderer, make_mesh


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',action='store_true')
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    output=ROOT/'.qa/creature-proof'
    output.mkdir(parents=True,exist_ok=True)
    pygame.display.init()
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
    flags=pygame.OPENGL|pygame.DOUBLEBUF
    if not args.preview:flags|=pygame.HIDDEN
    screen=pygame.display.set_mode((1920,1080),flags)
    pygame.display.set_caption('Bloc Fantome - isolated creature motion proof')
    gpu=PresentationRenderer()
    camera=Camera(screen.get_size())
    camera.angle=160
    camera.center=np.array((0,1,31.))
    camera.half=53
    cells=sanctuary()
    extracted={p:v for p,v in cells.items() if -12<=p[0]<=-9 and 16<=p[1]<=17 and 38<=p[2]<=39}
    intact=make_mesh(cells)
    damaged=make_mesh({p:v for p,v in cells.items() if p not in extracted})
    fragment=make_mesh(extracted)
    distant=make_mesh(distant_arches())
    for mesh in (intact,damaged,fragment):
        for data in mesh:data[:,:,5:8]*=(.40,.46,.50)
    for data in distant:data[:,:,5:8]*=.65
    process=None

    def render(t,read=False):
        pose=sample(t)
        mesh=body_mesh(pose)
        gpu.begin(camera,t)
        gpu.mesh(distant,camera)
        gpu.mesh(damaged if pose.pull else intact,camera)
        if pose.pull:gpu.mesh(fragment,camera,np.array((2,9,7))*pose.pull)
        gpu.gl.glDisable(0x0DE1)
        gpu.draw(mesh)
        result=gpu.capture(camera.size) if read else None
        gpu.gl.glFinish()
        pygame.display.flip()
        return result,len(mesh)

    try:
        for t,label in ((0,'arrival'),(3.4,'first-contact'),(7.6,'held-silhouette'),
                        (8.55,'contortion'),(9.7,'eye'),(13.5,'masonry-pull')):
            frame,quads=render(t,True)
            pygame.image.save(frame,output/f'{label}.png')
        camera.center=sample(9.7).head.copy();camera.half=6
        frame,_=render(9.7,True)
        pygame.image.save(frame,output/'eye-detail.png')
        camera.center=np.array((0,1,31.));camera.half=53
        timings=[]
        for i in range(130):
            start=time.perf_counter()
            _,quads=render(i/129*DURATION)
            if i>=10:timings.append((time.perf_counter()-start)*1000)
        report={'size':camera.size,'frames':len(timings),'p50_ms':float(np.percentile(timings,50)),
                'p95_ms':float(np.percentile(timings,95)),'max_ms':max(timings),
                'body_quads':quads,'gl_error':gpu.gl.glGetError(),
                'renderer':gpu.gl.glGetString(0x1F01).decode(),
                'python':sys.version,'pygame':pygame.version.ver,
                'scope':'Real native 1080p render, CPU articulation, glFinish and swap; silent isolated proof'}
        (output/'render-profile.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report),flush=True)
        if args.video:
            command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo',
                     '-pixel_format','rgb24','-video_size','1920x1080','-framerate','30',
                     '-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18',
                     '-pix_fmt','yuv420p','-movflags','+faststart',str(output/'motion-proof.mp4')]
            with (output/'ffmpeg.log').open('wb') as log:
                process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
                for frame in range(round(DURATION*30)):
                    for event in pygame.event.get():
                        if event.type==pygame.QUIT:raise InterruptedError('Native close requested')
                    surface,_=render(frame/30,True)
                    process.stdin.write(pygame.image.tobytes(surface,'RGB'))
                process.stdin.close()
                if process.wait(timeout=60):raise RuntimeError('Video encoding failed; see ffmpeg.log')
            print('Video complete',flush=True)
        if args.preview:
            clock=pygame.time.Clock();start=time.perf_counter();running=True
            while running and time.perf_counter()-start<DURATION:
                for event in pygame.event.get():
                    if event.type==pygame.QUIT:running=False
                render(time.perf_counter()-start)
                clock.tick(60)
    finally:
        if process is not None and process.poll() is None:
            process.terminate();process.wait(timeout=10)
        gpu.close()
        pygame.quit()


if __name__=='__main__':
    main()
