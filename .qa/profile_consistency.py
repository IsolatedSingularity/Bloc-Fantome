exec(open('.qa/audit_consistency.py').read().split('results=[]')[0])
import cProfile,pstats
app._applyWindowSize(1920,1080)
for name in ('plains','small_end_islands'):
    app._openBiomeScene(name);app.hoveredSourceBlock=None
    print(name,'bounds',app.world.occupiedBounds,'focus',app.cameraFocusZ,'zoom',app.zoomLevel,'offset',app.renderer.offsetX,app.renderer.offsetY,flush=True)
    for turn in range(4):
        profile=cProfile.Profile();profile.enable()
        app._rotateViewAndRecenter(1)
        for _ in range(8):app._render()
        profile.disable()
        print('VIEW',app.renderer.viewRotation,app.renderStats,'offset',app.renderer.offsetX,app.renderer.offsetY,flush=True)
        if name=='plains' and turn==0:pstats.Stats(profile).sort_stats('cumtime').print_stats(30)
app.worldLoadExecutor.shutdown(wait=True)
pygame.quit()
