from pathlib import Path
p=Path('.qa/sanctuary-preview/architecture.py');s=p.read_text();s=s.replace('''            top=round(2*(spring+rise*curve))
            for z''','''            top=round(2*(spring+rise*curve))
            adjacent=[]
            for neighbor in (u-1,u+1):
                d=min(1,abs((neighbor-.5)/(half*2)))
                adjacent.append(round(2*(spring+rise*math.sqrt(max(0,4-(d+1)**2))/math.sqrt(3))))
            rib_bottom=min(top,*adjacent)
            for z''').replace('or z>=top','or z>=rib_bottom')
s=s.replace('for d in range(1,4):put(sign*(5+d),y,19-d*2)','for d in range(1,4):\n                box(sign*(5+d),sign*(5+d),y,y,19-d*2,21-d*2)')
p.write_text(s)
