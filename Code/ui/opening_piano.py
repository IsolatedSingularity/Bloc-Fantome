"""Whole creator-marked piano chapters, with at most two decoded tracks.

Chapter boundaries come from the owner's original recording, not timed loops.
The queued chapter is decoded away from the presentation thread. Channel 30
remains separate from the paused editor music and the encounter score.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import logging
import random
import pygame
from runtime_paths import SOUNDS_DIR


class OpeningPiano:
    def __init__(self, mixer=pygame.mixer, executor_factory=ThreadPoolExecutor, shuffle=random.shuffle):
        self.mixer=mixer;self.executor_factory=executor_factory;self.shuffle=shuffle
        self.channel=None;self.executor=None;self.future=None
        self.current=None;self.queued=None;self.last_path=None;self.bag=[];self.paths=[]
        self.current_path=None;self.queued_path=None;self.pending_path=None

    def _next_path(self):
        if not self.bag:
            self.bag=list(self.paths);self.shuffle(self.bag)
            if len(self.bag)>1 and self.bag[-1]==self.last_path:
                self.bag[0],self.bag[-1]=self.bag[-1],self.bag[0]
        self.last_path=self.bag.pop()
        return self.last_path

    def start(self, volume, paths=None):
        self.close()
        root=Path(SOUNDS_DIR)/'opening'
        self.paths=list(paths) if paths is not None else sorted((root/'piano-chapters').glob('*.ogg'))
        if not self.paths and (root/'panoir-you-have-time.ogg').is_file():
            self.paths=[root/'panoir-you-have-time.ogg']
        if not self.paths or not self.mixer.get_init():return
        self.bag=[];self.channel=self.mixer.Channel(30)
        self.channel.set_volume(volume)
        self.current_path=self._next_path()
        self.current=self.mixer.Sound(str(self.current_path))
        self.channel.play(self.current,fade_ms=1800)
        self.executor=self.executor_factory(max_workers=1,thread_name_prefix='opening-piano')
        self._prepare_next()

    def _prepare_next(self):
        self.pending_path=self._next_path()
        self.future=self.executor.submit(self.mixer.Sound,str(self.pending_path))

    def update(self, volume, encounter=False):
        if encounter:
            self.close();return
        if self.channel is None:return
        self.channel.set_volume(volume)
        if self.future is not None and self.future.done():
            future,self.future=self.future,None
            try:
                self.queued=future.result()
                self.queued_path=self.pending_path
                self.channel.queue(self.queued)
            except (OSError,pygame.error) as error:
                logging.getLogger(__name__).warning('Piano chapter unavailable: %s',error)
        if self.queued is not None and self.channel.get_sound() is self.queued:
            self.current,self.queued=self.queued,None
            self.current_path,self.queued_path=self.queued_path,None
            self._prepare_next()

    def close(self):
        if self.current_path is not None:self.last_path=self.current_path
        if self.channel is not None:self.channel.stop()
        if self.future is not None:self.future.cancel()
        # Finish any decoder before the application can tear down SDL_mixer.
        if self.executor is not None:self.executor.shutdown(wait=True,cancel_futures=True)
        self.channel=self.executor=self.future=self.current=self.queued=None
        self.current_path=self.queued_path=self.pending_path=None
