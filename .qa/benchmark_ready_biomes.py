exec(open('.qa/audit_consistency.py').read().split('results=[]')[0])
app._applyWindowSize(1920,1080)
results=[]
for name in ('plains','warped_forest','end_highlands','small_end_islands'):
    start=time.perf_counter();app._queueBiomeScene(name)
    count=0
    while app.pendingBiomeLoad is not None:
        app.clock.tick(60);app._update();app._render();count+=1
        assert count<600,(name,'preparation stuck')
    row={'name':name,'ready_ms':round((time.perf_counter()-start)*1000,2),'turns':[]}
    settled=[]
    for frame in range(150):
        app.clock.tick(60)
        start=time.perf_counter();app._update();app._render()
        if frame>=120:settled.append((time.perf_counter()-start)*1000)
    row['settled_p95_ms']=round(sorted(settled)[28],2)
    for turn in range(8):
        app.clock.tick(60)
        start=time.perf_counter();app._rotateViewAndRecenter(1);app._update();app._render()
        row['turns'].append(round((time.perf_counter()-start)*1000,2))
        assert app.renderStats['drawn']>0
    print(row,flush=True);results.append(row)
Path('.qa/ready-biomes.json').write_text(json.dumps(results,indent=2))
app.worldLoadExecutor.shutdown(wait=True)
pygame.quit()
