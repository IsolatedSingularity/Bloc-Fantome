from pathlib import Path
p=Path('.qa/sanctuary-preview/architecture.py');s=p.read_text()
s=s.replace("        cells[(x,y,z)]=(b,t)","        for dx in (0,1):\n            for dy in (0,1):\n                for dz in (0,1):cells[(2*x+dx,2*y+dy,2*z+dz)]=(b,t)")
a=s.index('        for u in range(-half,half+1):');b=s.index('    # Single axial',a)
s=s[:a]+'''        for u in range(-half*2,half*2+2):
            distance=min(1,abs((u-.5)/(half*2)))
            curve=math.sqrt(max(0,4-(distance+1)**2))/math.sqrt(3)
            top=round(2*(spring+rise*curve))
            for z in range(base*2,top+2):
                rim=u<=-half*2+1 or u>=half*2 or z>=top
                if not rim and not glass:continue
                block=B.SMOOTH_QUARTZ if rim else B.LIGHT_BLUE_STAINED_GLASS
                tint='stone' if rim else 'glass'
                for thick in (0,1):
                    x,y=(center*2+u,fixed*2+thick) if axis=='x' else (fixed*2+thick,center*2+u)
                    cells[(x,y,z)]=(block,tint)
'''+s[b:]
s=s.replace('box(x,x,y,y,4,13,B.QUARTZ_PILLAR)','box(x,x,y,y,4,19,B.QUARTZ_PILLAR)').replace('y+1,12,12','y+1,18,18').replace("arch('x',y,0,5,13,6,base=13)","arch('x',y,0,5,19,6,base=19)")
s=s.replace("put(sign*(5+d),y,14-d)","put(sign*(5+d),y,19-d*2)")
p.write_text(s)
