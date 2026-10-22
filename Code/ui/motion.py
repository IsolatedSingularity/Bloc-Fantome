"""Small reversible opacity transitions with no input lock or frame-step timing."""
import math


class Opacity:
    def __init__(self):
        self.value = 0.0
        self.last = None

    def update(self, visible, now, reduced=False):
        dt = max(0, now-self.last) if self.last is not None else 1/60
        self.last = now
        target = float(visible)
        self.value = target if reduced else target+(self.value-target)*math.exp(-dt/.045)
        if abs(target-self.value)<.01:self.value=target
        return self.value
