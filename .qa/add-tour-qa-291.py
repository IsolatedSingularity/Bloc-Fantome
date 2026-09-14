from pathlib import Path
p=Path('tests/render_visual_checks.py');s=p.read_text(encoding='utf-8');a=s.index("if __name__ ==")
fn='''def render_tour(output_dir: Path):
    """Every demonstration and preview shelf, native resolutions and four camera views."""
    import json
    output_dir.mkdir(parents=True,exist_ok=True)
    app=app_module.BlocFantome()
    assert app.assetManager.loadAllAssets()
    app._generateStructurePreviews()
    app.tutorialScreen.setAssets(app.assetManager.buttonNormal,app.assetManager.buttonHover,
        app.assetManager.checkboxTexture,app.assetManager.checkboxSelectedTexture,app.assetManager.clickSound,app.assetManager)
    metrics=[]
    def settle():
        frames=[];deadline=time.perf_counter()+35
        while time.perf_counter()<deadline:
            t=time.perf_counter();app._update();app._render();frames.append((time.perf_counter()-t)*1000)
            if not getattr(app,'_pendingTourLoad',None) and app._worldSurfaceBuild is None:break
            time.sleep(.001)
        assert not getattr(app,'_pendingTourLoad',None),'Tour load timed out'
        for _ in range(3):app._render()
        return frames
    for width,height in ((1200,800),(960,640),(1920,1080)):
        app._applyWindowSize(width,height)
        app._beginTutorial(advanced=False)
        for i,step in enumerate(app.tutorialScreen.TUTORIAL_STEPS):
            start=time.perf_counter();app.tutorialScreen.selectLesson(i)
            dispatch=(time.perf_counter()-start)*1000
            frames=settle();ready=(time.perf_counter()-start)*1000
            save_capture(app.screen,output_dir/f"tour_{step['id']}_{width}.png")
            if width==1200:
                for rotation in range(1,4):
                    app._rotateViewAndRecenter(1);settle()
                    save_capture(app.screen,output_dir/f"tour_{step['id']}_view{rotation}.png")
                app._rotateViewAndRecenter(1);settle()
            stable=[]
            for _ in range(20):
                t=time.perf_counter();app._render();stable.append((time.perf_counter()-t)*1000)
            metrics.append(dict(page=step['id'],width=width,dispatch_ms=round(dispatch,2),ready_ms=round(ready,2),max_loading_frame_ms=round(max(frames),2),p95_ms=round(sorted(stable)[18],2)))
        app.tutorialScreen.optional=True;app._loadGuidedLesson(15);settle()
        save_capture(app.screen,output_dir/f'optional_chapel_{width}.png')
        app.tutorialScreen.minimized=True;app._render();save_capture(app.screen,output_dir/f'minimized_{width}.png')
        app.tutorialScreen.hide()
        app.blocksExpanded=app.experimentalExpanded=False
        for section in app.previewBrowser.SECTIONS:
            app.previewBrowser.expand(app,section);app.inventoryScroll=app.inventoryScrollTarget=0
            settle();save_capture(app.screen,output_dir/f'previews_{section}_{width}.png')
        for tab in app.library.TABS:
            app.library.open(app,tab)
            if app.library.entries:app.library.pending=app.library.entries[0]
            settle();save_capture(app.screen,output_dir/f'library_{tab.replace(" ","_")}_{width}.png')
        app.library.visible=False;app.settingsMenuOpen=True
        app._render();save_capture(app.screen,output_dir/f'settings_{width}.png')
        app.settingsMenuOpen=False;app.showShortcutsPanel=True
        app._render();save_capture(app.screen,output_dir/f'help_{width}.png');app.showShortcutsPanel=False
    (output_dir/'performance.json').write_text(json.dumps(metrics,indent=2))
    app.worldLoadExecutor.shutdown(wait=True);pygame.quit()


'''
s=s[:a]+fn+s[a:];s=s.replace('(render_consistency if',"(render_tour if '--tour' in sys.argv else render_consistency if")
p.write_text(s,encoding='utf-8')
