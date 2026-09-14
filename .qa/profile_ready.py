exec(open('.qa/audit_consistency.py').read().split('results=[]')[0])
import cProfile,pstats
app._applyWindowSize(1920,1080);app._queueBiomeScene('warped_forest')
while app.pendingBiomeLoad is not None:
    app.clock.tick(60);app._update();app._render()
p=cProfile.Profile();p.enable()
for turn in range(8):
    app.clock.tick(60);app._rotateViewAndRecenter(1);app._update();app._render()
p.disable();pstats.Stats(p).sort_stats('cumtime').print_stats(25)
app.worldLoadExecutor.shutdown(wait=True)
pygame.quit()
