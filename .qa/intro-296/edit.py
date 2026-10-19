from pathlib import Path
p=Path('Code/ui/opening_audio.py')
s=p.read_text().replace('import numpy as np','import math')
s=s.replace('self.last={}','self.last={}\n        self.orbit_gain=0.0')
s=s.replace("'turn':'block/grindstone/grindstone1.ogg',", "'orbit':'opening/orbit-bed.wav',\n                          'rise':'opening/sanctuary-rise.wav',")
a=s.index('        # A soft, band-limited'); b=s.index('    def play(',a)
s=s[:a]+'''    def update_orbit(self, speed, seconds):
        """One loop follows actual angular velocity, including its damped tail."""
        if 'orbit' not in self.sounds:return
        target=min(1.0,abs(speed)/90) if abs(speed)>.4 else 0.0
        self.orbit_gain+=(target-self.orbit_gain)*(1-math.exp(-max(0,seconds)*(12 if target>self.orbit_gain else 6)))
        channel=pygame.mixer.Channel(25)
        if self.orbit_gain>.002 and self.volume>0:
            channel.set_volume(self.volume*.32*self.orbit_gain)
            if not channel.get_busy():channel.play(self.sounds['orbit'],loops=-1,fade_ms=80)
        else:channel.stop()

'''+s[b:]
s=s.replace("'turn':.25,",'').replace("'rise':.65","'rise':.88").replace('(26,27,28,29)','(25,26,27,28,29)')
p.write_text(s)
p=Path('Code/ui/opening_scene.py');s=p.read_text()
s=s.replace('self.dragging=False\n        self.renderer', 'self.dragging=False\n        self.zoom=self.target_zoom=1.0\n        self.controls_at=self.READY_AT\n        self.renderer',1)
s=s.replace('self.overlay=pygame.Surface(size,pygame.SRCALPHA)','self.overlay=pygame.Surface(size,pygame.SRCALPHA)\n        self.controls=pygame.Surface(size,pygame.SRCALPHA)')
s=s.replace("dt=max(0,seconds);previous=self.elapsed;self.elapsed+=dt", "dt=max(0,seconds);previous=self.elapsed;self.elapsed+=dt\n        old_angle=self.renderer.angle\n        if self.size[1]-155<=self.pointer[1]<=self.size[1] or self.dragging:\n            self.controls_at=self.elapsed\n        if self.placed_at is not None and previous-self.placed_at<self.REVEAL_DURATION<=self.elapsed-self.placed_at:\n            self.controls_at=self.elapsed\n        if self.awakened_at is not None and previous-self.awakened_at<=1.2<self.elapsed-self.awakened_at:\n            self.controls_at=self.elapsed")
s=s.replace("self.phase='sanctuary'\n                self.renderer", "self.phase='sanctuary'\n                self.controls_at=self.elapsed\n                self.renderer")
s=s.replace('finish=self.SANCTUARY_OFFSET+(.5,-3,16)', 'finish=self.SANCTUARY_OFFSET+(.5,-3,20)')
s=s.replace('10.5+15.5*wide+20*arrive','10.5+15.5*wide+12*arrive')
s=s.replace('self.renderer.center=self.SANCTUARY_OFFSET+(.5,-3,16)','self.renderer.center=self.SANCTUARY_OFFSET+(.5,-3,20)')
s=s.replace('self.renderer.half=46*','self.renderer.half=38*')
s=s.replace('        # Less than three display pixels', '''        self.zoom+=(self.target_zoom-self.zoom)*(1-math.exp(-dt*10))
        self.renderer.half*=self.zoom
        self.audio.update_orbit((self.renderer.angle-old_angle)/dt if dt and self.orbit_enabled else 0,dt)
        # Less than three display pixels''')
s=s.replace("        self.audio.play('turn',self.elapsed)", '        self.controls_at=self.elapsed',1)
s=s.replace("            self.audio.play('turn',self.elapsed)", '            self.zoom=self.target_zoom=1.0')
s=s.replace("        if abs(desired-self.target_angle)>3:self.audio.play('turn',self.elapsed)", '        self.controls_at=self.elapsed')
s=s.replace('    def handle_event(self,event):', '''    @property
    def controls_alpha(self):
        return round(255*(1-ramp(self.elapsed-self.controls_at,3,.4)))

    def handle_event(self,event):''')
s=s.replace("        if event.type==pygame.WINDOWFOCUSLOST:self.dragging=False", """        if hasattr(event,'pos') and self.size[1]-155<=event.pos[1]<=self.size[1]:
            self.controls_at=self.elapsed
        if event.type==pygame.WINDOWFOCUSLOST:self.dragging=False
        if event.type==pygame.MOUSEWHEEL:
            if self.phase!='approach' and self.elapsed>=self.READY_AT:
                delta=getattr(event,'precise_y',event.y)
                if getattr(event,'flipped',False):delta=-delta
                self.target_zoom=max(.55,min(1.5,self.target_zoom*math.exp(-max(-20,min(20,delta))*.12)))
                self.controls_at=self.elapsed
            return""")
# Draw controls on their own native-size layer so geometry/hover highlights stay visible.
needle='        if self.orbit_enabled:\n            for rect,label,direction'
s=s.replace(needle,'        surface=self.controls;surface.fill((0,0,0,0))\n        if self.orbit_enabled:\n            for rect,label,direction')
s=s.replace('        if self.elapsed<3.85:', '        surface.set_alpha(self.controls_alpha)\n        self.overlay.blit(surface,(0,0))\n        surface=self.overlay\n        if self.elapsed<3.85:')
p.write_text(s)
for filename in ('Code/blocFantome.py','Code/build_exe.py','Code/installer.iss'):
    p=Path(filename);p.write_text(p.read_text(encoding='utf-8').replace('2.9.5','2.9.6'),encoding='utf-8')
