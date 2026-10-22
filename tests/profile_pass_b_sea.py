"""Compare old/new sea meshes under the same hidden WGL scene and camera."""
import os,sys,json,time,subprocess,types
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows';os.environ['SDL_AUDIODRIVER']='dummy'
import pygame
from ui.opening_scene import OpeningScene
from ui.opening_environment import AbyssGround
from ui.presentation_renderer import PresentationRenderer


def main():
    out=ROOT/'.qa/pass-b/sea';out.mkdir(parents=True,exist_ok=True)
    old=types.ModuleType('baseline_ground')
    source=subprocess.run(['git','show','80df4d74:Code/ui/opening_environment.py'],cwd=ROOT,
                          capture_output=True,text=True,check=True).stdout
    exec(compile(source,'baseline_ground','exec'),old.__dict__)
    pygame.init();pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
    screen=pygame.display.set_mode((1920,1080),pygame.HIDDEN|pygame.OPENGL|pygame.DOUBLEBUF)
    scene=OpeningScene((1920,1080),None,effects_volume=0);scene.gpu=PresentationRenderer()
    grounds={'baseline':old.AbyssGround(),'pass_b':AbyssGround()}
    result={name:dict(mesh_ms=[],frame_ms=[],triangles=len(ground.indices)) for name,ground in grounds.items()}
    try:
        scene.update(5);scene.place();scene.update(5);scene.activate('door');scene.update(scene.RISE_DURATION)
        for i in range(120):
            for name in (('baseline','pass_b') if i%2 else ('pass_b','baseline')):
                scene.ground=grounds[name];scene.elapsed=30+i/30
                start=time.perf_counter();scene.ground.mesh(scene.elapsed)
                result[name]['mesh_ms'].append((time.perf_counter()-start)*1000)
                start=time.perf_counter();scene.update(0);scene.render(screen);scene.gpu.gl.glFinish()
                result[name]['frame_ms'].append((time.perf_counter()-start)*1000)
                pygame.display.flip()
        for name in result:
            for key in ('mesh_ms','frame_ms'):
                result[name][key+'_p95']=float(np.percentile(result[name][key],95))
        (out/'matched.json').write_text(json.dumps(result,indent=2))
        print({k:{n:v for n,v in r.items() if not isinstance(v,list)} for k,r in result.items()})
    finally:scene.close();pygame.quit()


if __name__=='__main__':main()
