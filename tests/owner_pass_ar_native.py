"""Isolated native QA harness. Starts hidden; command.json stages app state, OS input remains external."""
import os,sys,pathlib,json,time,traceback
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Code'))
os.environ['SDL_VIDEODRIVER']='windows'
import pygame,blocFantome as b,runtime_paths
original_mode=pygame.display.set_mode
def hidden_mode(size,flags=0,*args,**kwargs):return original_mode(size,flags|pygame.HIDDEN,*args,**kwargs)
pygame.display.set_mode=hidden_mode
OUT=ROOT/'.qa/owner-pass-ar'/('native-ui' if '--ui' in sys.argv else 'native-after')
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'saves').mkdir(exist_ok=True)
b.DERIVED_WORLD_CACHE_DIR=str(OUT/'native-cache')
with patch.object(b,'APP_CONFIG_FILE',str(OUT/'isolated-config.json')),patch.object(b,'SAVES_DIR',str(OUT/'saves')),patch.object(runtime_paths,'SAVES_DIR',str(OUT/'saves')),patch.object(b.BlocFantome,'_saveAppConfig'),patch.object(b.TutorialScreen,'_saveConfig'):
 app=b.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
 app.assetManager.loadAllAssets();app._generateStructurePreviews();app._createInitialFloor()
 if '--ui' not in sys.argv:app._loadBuildingFromPath(str(ROOT/'Code/worlds/ocean_monument_1161.json.gz'),silent=True)
 app._fitWorldToViewport();app.selectedBlock=b.BlockType.GOLD_BLOCK
 pygame.display.set_caption('Bloc Fantome | PASS A-R | isolated native QA')
 trace=[]
 original_down=app._handleMouseDown
 def traced_down(event):
  source=app.hoveredSourceBlock;target=app.hoveredCell
  old=app.world.getBlock(*target).name if target else None
  start=time.perf_counter();original_down(event);elapsed=(time.perf_counter()-start)*1000
  changed=[(target,old,app.world.getBlock(*target).name)] if target and app.world.getBlock(*target).name!=old else []
  row=dict(input='OS mouse',pos=event.pos,button=event.button,source=source,target=target,face=app.hoveredFace,changed=changed,handler_ms=elapsed)
  if source and app.hoveredFace:
   x,y,z=source;rot=app.renderer.viewRotation
   dx,dy={'top':(0,0),'left':((0,1),(1,0),(0,-1),(-1,0))[rot],'right':((1,0),(0,-1),(-1,0),(0,1))[rot]}[app.hoveredFace]
   dest=(x+dx,y+dy,z+(app.hoveredFace=='top'));row['adjacent']=dest;row['adjacent_type']=app.world.getBlock(*dest).name
  trace.append(row);(OUT/'clicks.json').write_text(json.dumps(trace,indent=2))
 app._handleMouseDown=traced_down
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
    if data.get('show'):
     pygame.display.set_mode=original_mode;app._applyWindowSize(1200,800)
     pygame.display.set_caption('Bloc Fantome | PASS A-R | isolated native QA')
    if data.get('hide'):
     pygame.display.set_mode=hidden_mode;app._applyWindowSize(1200,800)
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
    if data.get('lesson'):
     from engine.tutorial_lessons import TOUR
     step=next(s for s in TOUR if s['id']==data['lesson'])
     app._beginTutorial(advanced=False);app._cancelTourLoad(navigating=True)
     app.tutorialScreen.currentStep=TOUR.index(step)
     app._applyTourScene(app._stageTourScene(step),step)
    if data.get('undo'):app.workshop.act('undo',app)
    if data.get('redo'):app.workshop.act('redo',app)
    if data.get('reopen'):app._loadBuildingFromPath(str(OUT/'saves/native.json.gz'),silent=True)
    if data.get('home'):app.library.open(app)
    if 'library_tab' in data:app.library.change_view(app,data['library_tab'])
    if data.get('library_back'):app.library.change_view(app)
    if 'pan' in data:app.renderer.offsetX+=data['pan'];app.targetOffsetX=app.renderer.offsetX
    if data.get('floor'):
     app.tutorialScreen.visible=False;app._createInitialFloor();app._fitWorldToViewport()
    if data.get('check_cells'):
     cells={str(row['target']):app.world.getBlock(*row['target']).name for row in trace if row['target']}
     (OUT/(data['check_cells']+'.json')).write_text(json.dumps(cells,indent=2))
    if 'zoom' in data:app._handleZoom(data['zoom'],600,400)
    if data.get('save'):app._saveBuilding(filepath=str(OUT/'saves/native.json.gz'),silent=True)
    if data.get('stop'):break
   started=time.perf_counter();app._handleEvents();app._update();app._render()
   if trace and 'visible_ms' not in trace[-1]:
    trace[-1]['visible_ms']=(time.perf_counter()-started)*1000
    pygame.image.save(app.screen,OUT/('click-%02d.png'%len(trace)))
    (OUT/'clicks.json').write_text(json.dumps(trace,indent=2))
   app.clock.tick(60);frame+=1
   if recorder and time.monotonic()>=record_next:
    recorder.stdin.write(pygame.image.tostring(app.screen,'RGB'));record_next+=.05
   if last:
    pygame.image.save(app.screen,OUT/(last+'.png'));last=''
   if frame%15==0:
    (OUT/'state.json').write_text(json.dumps(dict(size=app.screen.get_size(),driver=pygame.display.get_driver(),viewport=app._worldViewportRight(),selected=app.selectedBlock.name,page=app.workshop.page,query=app.workshop.query,blocks=len(app.world.blocks),undo=len(app.undoManager.get_undo_history()),scroll=app.workshop.scroll,shortcuts=app.workshop.shortcut_scroller.position,count=len(app.workshop.filtered_blocks(app)),hover=app.hoveredCell,source=app.hoveredSourceBlock,metadata=app.sceneMetadata,revision=app.world.revision,camera=[app.renderer.offsetX,app.renderer.offsetY,app.zoomLevel],actions=[(list(r),a,e) for r,a,e in app.workshop.hits],error=app.workshop.error,frames=frame,visibility=vars(app.workshop.visibility),panning=app.panning,slider=app.draggingSlider,mouse=pygame.mouse.get_pos(),capture=list(app.workshop.captured),tutorial=app.tutorialScreen.visible),indent=2,default=str))
 finally:
  if recorder:recorder.stdin.close();recorder.wait()
  app.worldLoadExecutor.shutdown(wait=True,cancel_futures=True);pygame.quit()
