import os,sys,pathlib,json,time,traceback
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows'
import pygame,blocFantome as b,runtime_paths
OUT=pathlib.Path(__file__).resolve().parent
(OUT/'saves').mkdir(exist_ok=True)
b.DERIVED_WORLD_CACHE_DIR=str(OUT/'native-cache')
with patch.object(b,'APP_CONFIG_FILE',str(OUT/'isolated-config.json')),patch.object(b,'SAVES_DIR',str(OUT/'saves')),patch.object(runtime_paths,'SAVES_DIR',str(OUT/'saves')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
 app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
 app.assetManager.loadAllAssets();app._generateStructurePreviews();app._createInitialFloor()
 app.selectedBlock=b.BlockType.OAK_STAIRS
 for x in range(3,9):
  for y in range(3,9):app.world.setBlock(x,y,1,b.BlockType.STONE_BRICKS)
 for x,y in ((3,3),(3,8),(8,3),(8,8)):
  for z in range(2,6):app.world.setBlock(x,y,z,b.BlockType.QUARTZ_PILLAR)
 for x in range(3,9):
  for y in (3,8):app.world.setBlock(x,y,6,b.BlockType.SMOOTH_QUARTZ)
 app._fitWorldToViewport();pygame.display.set_caption('Bloc Fantome | OWNER PASS A | isolated review')
 original_get=pygame.event.get
 def logged_events():
  events=original_get()
  with (OUT/'input-events.jsonl').open('a') as log:
   for e in events:
    if e.type in (pygame.KEYDOWN,pygame.KEYUP,pygame.TEXTINPUT,pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP,pygame.MOUSEWHEEL):log.write(json.dumps(dict(type=pygame.event.event_name(e.type),**e.dict),default=str)+'\n')
  return events
 pygame.event.get=logged_events
 recorder=None;record_next=0
 frame=0;last='';deadline=time.monotonic()+3600
 try:
  while app.running and time.monotonic()<deadline:
   command=OUT/'command.json'
   if command.exists():
    try:data=json.loads(command.read_text())
    except json.JSONDecodeError:data={}
    else:command.unlink()
    if data.get('record'):
     import subprocess
     recorder=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1200x800','-framerate','20','-i','-','-an','-c:v','libx264','-preset','ultrafast','-crf','23',str(OUT/'native-input.mp4')],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     record_next=time.monotonic()
    if data.get('stop_record') and recorder:
     recorder.stdin.close();recorder.wait();recorder=None
    if 'size' in data:app._applyWindowSize(*data['size'])
    if 'action' in data:app.workshop.act(data['action'],app)
    if 'query' in data:app.workshop.query=data['query']
    if 'close_modals' in data:app.library.visible=False;app.settingsMenuOpen=False;app.showShortcutsPanel=False
    if 'text_scale' in data:
     from ui.fonts import set_text_scale
     app.workshop.text_scale=data['text_scale'];set_text_scale(data['text_scale'])
    if 'state' in data:
     for k,v in data['state'].items():setattr(app,k,v)
    if 'capture' in data:last=data['capture']
    if data.get('stop'):break
   app._handleEvents();app._update();app._render();app.clock.tick(60);frame+=1
   if recorder and time.monotonic()>=record_next:
    recorder.stdin.write(pygame.image.tostring(app.screen,'RGB'));record_next+=.05
   if last:
    pygame.image.save(app.screen,OUT/(last+'.png'));last=''
   if frame%60==0:
    (OUT/'state.json').write_text(json.dumps(dict(size=app.screen.get_size(),driver=pygame.display.get_driver(),viewport=app._worldViewportRight(),selected=app.selectedBlock.name,page=app.workshop.page,query=app.workshop.query,blocks=len(app.world.blocks),undo=len(app.undoManager.get_undo_history()),scroll=app.workshop.scroll,shortcuts=app.workshop.shortcut_scroller.position,count=len(app.workshop.filtered_blocks(app)),revision=app.world.revision,camera=[app.renderer.offsetX,app.renderer.offsetY,app.zoomLevel],actions=[(list(r),a,e) for r,a,e in app.workshop.hits],error=app.workshop.error,frames=frame,visibility=vars(app.workshop.visibility),panning=app.panning,slider=app.draggingSlider,mouse=pygame.mouse.get_pos(),capture=list(app.workshop.captured),tutorial=app.tutorialScreen.visible),indent=2))
 finally:
  if recorder:recorder.stdin.close();recorder.wait()
  app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()


