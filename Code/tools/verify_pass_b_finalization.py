"""Opt-in native, real-time startup/map/save/exit probe with isolated user data."""
from pathlib import Path
from time import perf_counter
import json
import sys
import pygame
from tools.verify_review_audio import temporary_attribute


def run(output, module):
    from ui import feedback, opening_scene
    import runtime_paths
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    evidence=out.parent
    original_mode=pygame.display.set_mode
    def hidden(size,flags=0,*args,**kwargs):
        return original_mode(size,flags|pygame.HIDDEN,*args,**kwargs)
    records=[];frames=[];cues=[];operations=[];last_capture={};start=perf_counter();state={'phase':'startup','map_visits':0}
    original_flip=pygame.display.flip
    def flip():
        original_flip()
        now=perf_counter()-start
        records.append({'seconds':now,'phase':state['phase'],'visit':state['map_visits']})
        if now-last_capture.get(state['phase'],-1)>=1/15 and len(frames)<240:
            frames.append((now,state['phase'],pygame.display.get_surface().copy()))
            last_capture[state['phase']]=now
    original_play=feedback.play
    def play(assets,name):
        result=original_play(assets,name)
        if result is not None:
            from engine.audio import DEFAULT_CHANNEL_GROUPS
            channel=next((index for group,pool in assets.audioRouter._groups.items()
                          for index,owned in zip(DEFAULT_CHANNEL_GROUPS[group],pool) if owned is result),None)
            cues.append({'seconds':perf_counter()-start,'cue':name,'channel':channel})
        return result
    with temporary_attribute(pygame.display,'set_mode',hidden), temporary_attribute(pygame.display,'flip',flip), \
         temporary_attribute(feedback,'play',play), \
         temporary_attribute(module,'APP_CONFIG_FILE',str(evidence/'isolated-config.json')), \
         temporary_attribute(module,'SAVES_DIR',str(evidence/'saves')), \
         temporary_attribute(runtime_paths,'SAVES_DIR',str(evidence/'saves')), \
         temporary_attribute(opening_scene,'CONFIG_PATH',str(evidence/'opening-config.json')):
        app=module.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        display_driver=pygame.display.get_driver();mixer_format=pygame.mixer.get_init()
        app.tutorialScreen.shouldShowOnStartup=lambda:False
        app.effectsMuted=True;app.musicMuted=True;app.ambientMuted=True
        events=app._handleEvents;phase_start=[0];steps=[0]
        def tick():
            events()
            if perf_counter()-start>45:raise TimeoutError(f'Probe stalled: {state}, {app.workshop.error}')
            if state['phase']=='map' and not app.worldMapActive and app._mapTransition is None:
                raise RuntimeError(app.workshop.error or 'Map preparation ended without activation')
            phase=state['phase']
            if phase=='startup':
                assert app.openingScene is None
                state['phase']='editor';phase_start[0]=perf_counter()
            elif phase=='editor' and perf_counter()-phase_start[0]>.15:
                pygame.image.save(app.screen,str(evidence/'editor.png'))
                state['phase']='map';phase_start[0]=perf_counter();app._requestWorldMap()
            elif phase=='map' and app.worldMapActive and app._mapTransition is None:
                operations.append({'warm':state['map_visits']>0,'map_total_ms':(perf_counter()-phase_start[0])*1000,
                    'preparation':[(name,stamp-start) for name,stamp in app.worldMapView.source_map.preparation_timeline]})
                pygame.image.save(app.screen,str(evidence/'map.png'))
                app._exitWorldMap();state['map_visits']+=1
                if state['map_visits']==1:
                    phase_start[0]=perf_counter();app._requestWorldMap()
                else:
                    state['phase']='library';steps[0]=0
            elif phase=='library':
                dimensions=('overworld','nether','end');tabs=app.library.TABS
                n=steps[0]
                if n<24:
                    t=perf_counter();app.library.dimension=dimensions[(n//4)%3]
                    app.library.visible=True;app.library.home=False;app.library.tab=tabs[n%4]
                    app.library.refresh(app);app.library.render(app)
                    operations.append({'library':tabs[n%4],'dimension':app.library.dimension,
                        'warm':n>=12,'ms':(perf_counter()-t)*1000})
                    steps[0]+=1
                else:
                    app.library.visible=False;state['phase']='weather';steps[0]=0
                    t=perf_counter();app._toggleHorrorRain()
                    operations.append({'horror_enable_ms':(perf_counter()-t)*1000})
            elif phase=='weather':
                steps[0]+=1
                if steps[0]==12:
                    assert app.horrorRainEnabled and app.horrorRainDrops
                    pygame.image.save(app.screen,str(evidence/'horror-rain.png'))
                    app._toggleHorrorRain()
                    assert not app.horrorRainDrops and app.horrorRainSoundChannel is None
                    operations.append({'horror_rendered_frames':12,'horror_cleanup':True})
                    state['phase']='button';app.workshop.act('settings',app)
            elif phase=='button':
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0))
                blocker=evidence/'blocked-destination';blocker.write_text('preserve',encoding='utf-8')
                app._saveBuilding(filepath=str(blocker/'failed.gz'));state['phase']='error'
            elif phase=='error' and getattr(app,'_pendingSave',None) is None:
                assert app.workshop.error and app.running
                operations.append({'failed_save_retained_world':True})
                app.workshop.error='';state['phase']='save'
                app.currentBuildPath=str(evidence/'saves'/'manual.json.gz')
                app._saveBuilding()
            elif phase=='save' and getattr(app,'_pendingSave',None) is None:
                operations.append({'save':getattr(app,'_lastSaveMetrics',{})})
                state['phase']='exit';app._requestExit()
                app._render();pygame.image.save(app.screen,str(evidence/'exit.png'))
            elif phase=='exit':
                state['phase']='shutdown';app._exitAction('exit')
        app._handleEvents=tick
        try:
            app.run()
            metrics=app._startupMetrics
            first=metrics['run_started']
            result={'display_driver':display_driver,'mixer_format':mixer_format,'frozen':bool(getattr(sys,'frozen',False)),'hidden':True,'physical_input':False,
                'human_listening':False,'audio_muted':True,
                'startup_ms':{k:(v-first)*1000 for k,v in metrics.items()},
                'presented_frames':records,'cues':cues,'operations':operations}
            for phase in ('startup','map','weather','shutdown'):
                times=[row['seconds'] for row in records if row['phase']==phase]
                result[phase+'_frame_count']=len(times)
                result[phase+'_max_frame_gap_ms']=max((b['seconds']-a['seconds'] for a,b in zip(records,records[1:]) if a['phase']==b['phase']==phase and a['visit']==b['visit']),default=0)*1000
            out.write_text(json.dumps(result,indent=2),encoding='utf-8')
            for phase in ('map','shutdown','audition'):
                selected=[row for row in frames if phase=='audition' or row[1]==phase]
                lines=[]
                for index,(timestamp,_phase,surface) in enumerate(selected):
                    name=f'{phase}-{index:03}.png';pygame.image.save(surface,str(evidence/name))
                    duration=selected[index+1][0]-timestamp if index+1<len(selected) else 1/60
                    lines.extend([f"file '{name}'",f'duration {duration:.6f}'])
                if selected:lines.append(f"file '{phase}-{len(selected)-1:03}.png'")
                (evidence/(phase+'.ffconcat')).write_text('\n'.join(lines),encoding='utf-8')
        except Exception:
            import traceback
            out.with_suffix('.error.txt').write_text(traceback.format_exc(),encoding='utf-8')
            app.worldLoadExecutor.shutdown(wait=False,cancel_futures=True)
            if hasattr(app,'_mapExecutor'):app._mapExecutor.shutdown(wait=False,cancel_futures=True)
            pygame.quit()
            raise
