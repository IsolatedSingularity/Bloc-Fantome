"""Opt-in native, real-time startup/map/save/exit probe with isolated user data."""
from pathlib import Path
from time import perf_counter
import json
import sys
import pygame
from tools.verify_review_audio import temporary_attribute


def run(output, module, *, polish=False, acceptance=False):
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
        if now-last_capture.get(state['phase'],-1)>=1/15 and len(frames)<480:
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
         temporary_attribute(runtime_paths,'BASE_DIR',str(evidence)), \
         temporary_attribute(opening_scene,'CONFIG_PATH',str(evidence/'opening-config.json')):
        app=module.BlocFantome();app.autoSaveEnabled=False;app.tutorialScreen.visible=False
        display_driver=pygame.display.get_driver();mixer_format=pygame.mixer.get_init();display_flags=app.screen.get_flags()
        assert not app.tutorialScreen.shouldShowOnStartup()
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
                assert not app.tutorialScreen.visible
                import ctypes
                operations.append({'tutorial_manual':True,'introduction_manual':True,
                    'os_dpi':ctypes.windll.user32.GetDpiForWindow(pygame.display.get_wm_info()['window'])})
                if polish:
                    assert app.skyboxesEnabled
                    assert all(block==module.BlockType.GRASS for (x,y,z),block in app.world.blocks.items() if z==0)
                    operations.append({'fresh_grass_floor':True,'skyboxes_default_on':True})
                state['phase']='editor';phase_start[0]=perf_counter()
            elif phase=='editor' and perf_counter()-phase_start[0]>.15:
                pygame.image.save(app.screen,str(evidence/'editor.png'))
                if polish:
                    state['phase']='palette';steps[0]=0;app.workshop.open_drawer('menu',app)
                else:
                    state['phase']='map';phase_start[0]=perf_counter();app._requestWorldMap()
            elif phase=='palette':
                steps[0]+=1
                if steps[0]%6==0:
                    pygame.image.save(app.screen,str(evidence/f'palette-{steps[0]//6}.png'))
                    if steps[0]<24:
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RIGHT,mod=0))
                    else:
                        app.workshop.close_drawer(app);state['phase']='map';phase_start[0]=perf_counter();app._requestWorldMap()
            elif phase=='map' and app.worldMapActive and app._mapTransition is None:
                operations.append({'warm':state['map_visits']>0,'map_total_ms':(perf_counter()-phase_start[0])*1000,
                    'preparation':[(name,stamp-start) for name,stamp in app.worldMapView.source_map.preparation_timeline]})
                pygame.image.save(app.screen,str(evidence/'map.png'))
                app._exitWorldMap();state['map_visits']+=1
                if state['map_visits']==1:
                    phase_start[0]=perf_counter();app._requestWorldMap()
                else:
                    state['phase']='map-audio-tail' if polish else 'library';steps[0]=0
            elif phase=='map-audio-tail':
                # Preserve map musical ownership; audition Library once its tail ends.
                if not any(pygame.mixer.Channel(i).get_busy() for i in (27,28)):
                    state['phase']='library'
            elif phase=='library':
                dimensions=('overworld','nether','end');tabs=app.library.TABS
                n=steps[0]
                if n<24:
                    if polish and n==0:
                        before=len(cues);app.library.open(app)
                        assert [row['cue'] for row in cues[before:]]==['close']
                        operations.append({'library_open_one_close_cue':True})
                    t=perf_counter();app.library.dimension=dimensions[(n//4)%3]
                    app.library.visible=True;app.library.home=False;app.library.tab=tabs[n%4]
                    app.library.refresh(app);app.library.render(app)
                    operations.append({'library':tabs[n%4],'dimension':app.library.dimension,
                        'warm':n>=12,'ms':(perf_counter()-t)*1000})
                    steps[0]+=1
                else:
                    if polish:
                        before=len(cues)
                        app.library.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,mod=0),app)
                        assert [row['cue'] for row in cues[before:]]==['close']
                        operations.append({'library_close_one_close_cue':True})
                        state['phase']='world-controls';steps[0]=0;app.workshop.page='world'
                        return
                    app.library.visible=False;state['phase']='weather';steps[0]=0
                    t=perf_counter();app._toggleHorrorRain()
                    operations.append({'horror_enable_ms':(perf_counter()-t)*1000})
            elif phase=='world-controls':
                steps[0]+=1
                if steps[0]==12:
                    pygame.image.save(app.screen,str(evidence/'world-controls.png'))
                    app.workshop.close_drawer(app)
                    if acceptance:
                        state['phase']='interaction';phase_start[0]=perf_counter();steps[0]=0
                    else:state['phase']='button';app.workshop.act('settings',app)
            elif phase=='interaction':
                # Real presentation timestamps; deliberately irregular frames
                # and rapid reversals, with hit regions checked while moving.
                n=steps[0];steps[0]+=1
                if n in (0,3,5,18):app.workshop.open_drawer('menu',app)
                if n==22:app.library.open(app)
                if n in (28,32):app.library.change_view(app,'Worlds')
                if n in (30,42):app.library.change_view(app)
                if n==46:
                    app._applyWindowSize(960,640)
                    operations.append({'resized_to':[960,640]})
                if n==52:
                    app.library.visible=False;app.workshop.visibility.reduced_motion=True
                    app.workshop.open_drawer('tools',app)
                if n==56:
                    assert app.workshop._drawer_opacity.value==1
                    operations.append({'reduced_motion_snap':True})
                    app.workshop.close_drawer(app)
                if n==60:
                    app.workshop.visibility.reduced_motion=False
                    app._applyWindowSize(1200,800)
                    app.workshop.act('tutorial',app)
                if n>=66 and app.tutorialScreen.visible and not getattr(app,'_pendingTourLoad',None):
                    pygame.image.save(app.screen,str(evidence/'tutorial-manual.png'))
                    app.tutorialScreen.minimized=True
                    state['phase']='tutorial-dock';phase_start[0]=perf_counter()
                if n in (6,29,47):pygame.time.wait(45)
            elif phase=='tutorial-dock' and perf_counter()-phase_start[0]>.3:
                pygame.image.save(app.screen,str(evidence/'tutorial-dock.png'))
                app.tutorialScreen.hide()
                operations.append({'manual_tutorial_open_minimize_leave':True})
                state['phase']='button';app.workshop.act('settings',app)
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
                if polish:
                    action=app._exitDialog.handle(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
                    app._exitAction(action);assert app.running and app._exitDialog is None
                    app._requestExit();assert app._exitDialog.focus=='stay'
                # This interaction script does not visit every semantic sound.
                # Audition the remaining decoder/router contracts explicitly;
                # keep these separate from cues observed through UI actions.
                remaining=set(feedback.CUES)-{row['cue'] for row in cues}-{'shutdown'}
                for name in sorted(remaining):
                    channel=feedback.play(app.assetManager,name)
                    assert channel is not None, ('cue audition rejected',name)
                    assert channel.get_sound() is app.assetManager._selected_cues[name]
                    channel.stop()
                operations.append({'explicit_cue_auditions':sorted(remaining)})
                state['phase']='shutdown';app._exitAction('exit')
        app._handleEvents=tick
        try:
            app.run()
            metrics=app._startupMetrics
            assert 'editor_ready' in metrics, 'Startup did not reach the editor; check packaged Assets'
            assert state['phase']=='shutdown' and state['map_visits']==2, 'Probe did not finish all interactions'
            assert set(feedback.CUES) <= {row['cue'] for row in cues}, 'Selected cue coverage incomplete'
            first=metrics['run_started']
            result={'display_driver':display_driver,'mixer_format':mixer_format,'frozen':bool(getattr(sys,'frozen',False)),'hidden':True,'physical_input':False,
                'human_listening':False,'audio_muted':True,
                'startup_ms':{k:(v-first)*1000 for k,v in metrics.items()},
                'polish':polish,'acceptance':acceptance,'display_flags':display_flags,
                'vsync_supported':False,'vsync_reason':'Native software RESIZABLE display; neither SCALED nor OPENGL',
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
