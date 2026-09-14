"""Local vanilla server control for reproducible, naturally generated captures."""
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]


class VanillaServer:
    def __init__(self, work, world='world', port=25592):
        self.work = Path(work)
        self.world = world
        self.port = port

    def __enter__(self):
        self.work.mkdir(parents=True, exist_ok=True)
        properties = self.work / 'server.properties'
        self.original_properties = properties.read_bytes() if properties.exists() else None
        (self.work / 'eula.txt').write_text('eula=true\n')
        # A dedicated capture directory; never a player save or public server.
        (self.work / 'server.properties').write_text(
            f'server-ip=127.0.0.1\nserver-port={self.port}\nonline-mode=false\n'
            f'level-name={self.world}\nlevel-seed=1\nview-distance=2\n'
            'max-tick-time=-1\nsync-chunk-writes=true\n')
        jar = ROOT / 'Game Reference/01_upstream/minecraft-1.16.1-server.jar'
        self.log = (self.work / 'capture-292.log').open('a', encoding='utf-8')
        self.messages = queue.Queue()
        self.process = subprocess.Popen(['java', '-Xmx3G', '-jar', str(jar), 'nogui'],
            cwd=self.work, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        def reader():
            for line in self.process.stdout:
                self.log.write(line); self.log.flush(); self.messages.put(line)
        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()
        try:
            self.wait(r'Done \(', 240)
            self.command('gamerule randomTickSpeed 0', 'Gamerule')
            self.command('gamerule doMobSpawning false', 'Gamerule')
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def wait(self, pattern, timeout=120):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try: line = self.messages.get(timeout=1)
            except queue.Empty:
                if self.process.poll() is not None: raise RuntimeError('Capture server exited')
                continue
            if re.search(pattern, line): return line.strip()
        raise TimeoutError(pattern)

    def command(self, command, pattern=None, timeout=120):
        self.process.stdin.write(command + '\n'); self.process.stdin.flush()
        return self.wait(pattern, timeout) if pattern else None

    def locate(self, dimension, kind, x, z, biome=False):
        dim = {'nether':'the_nether', 'end':'the_end'}.get(dimension, dimension)
        if not biome:
            kind = kind.split(':')[-1].lower()
        line = self.command(f'execute in minecraft:{dim} positioned {x} 64 {z} run '
            f'{"locatebiome" if biome else "locate"} {kind}',
            r'(nearest|Could not find|No biome|Unknown|Incorrect argument)', 180)
        match = re.search(r'\[(-?\d+),[^,]+, (-?\d+)\]', line)
        return ([int(match[1]), int(match[2])] if match else None), line

    def generate(self, dimension, origin, size):
        dim = {'nether':'the_nether', 'end':'the_end'}.get(dimension, dimension)
        x, z = origin; width, depth = size
        # Vanilla permits 256 force-loaded chunks. Larger surveys use strips.
        for sx in range(x, x + width, 128):
            for sz in range(z, z + depth, 128):
                ex, ez = min(sx + 127, x + width - 1), min(sz + 127, z + depth - 1)
                self.command(f'execute in minecraft:{dim} run forceload add {sx} {sz} {ex} {ez}',
                    r'(Marked|already marked)')
                time.sleep(2)
                self.command('save-all flush', 'Saved the game', 240)
                from engine.anvil import _read_region_chunk
                region = self.work / self.world / {'nether':'DIM-1','end':'DIM1'}.get(dimension,'') / 'region'
                for attempt in range(30):
                    ready = True
                    for cx in range(sx//16, ex//16+1):
                        for cz in range(sz//16, ez//16+1):
                            chunk = _read_region_chunk(region/f'r.{cx//32}.{cz//32}.mca',cx,cz)
                            if not chunk or chunk['Level']['Status'] != 'full': ready = False
                    if ready: break
                    time.sleep(2)
                    self.command('save-all flush', 'Saved the game', 240)
                else: raise RuntimeError(f'Chunks not ready: {sx}, {sz}')
                self.command(f'execute in minecraft:{dim} run forceload remove {sx} {sz} {ex} {ez}',
                    r'(Unmarked|No force|not marked|unexpected error)')

    def __exit__(self, *args):
        if self.process.poll() is None:
            self.command('stop')
            try: self.process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                self.process.terminate(); self.process.wait(timeout=30)
        self.thread.join(timeout=5)
        self.log.close()
        if self.original_properties is not None:
            (self.work / 'server.properties').write_bytes(self.original_properties)
