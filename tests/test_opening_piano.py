from concurrent.futures import Future
from types import SimpleNamespace
from ui.opening_piano import OpeningPiano


class Channel:
    current=None;queued=None
    def play(self,sound,**kwargs):self.current=sound
    def queue(self,sound):self.queued=sound
    def get_sound(self):return self.current
    def set_volume(self,value):self.volume=value
    def stop(self):self.current=self.queued=None


class Executor:
    def __init__(self,**kwargs):self.closed=False
    def submit(self,function,*args):
        result=Future();result.set_result(function(*args));return result
    def shutdown(self,**kwargs):self.closed=True


def test_whole_chapters_queue_without_repeating_and_encounter_stops():
    channel=Channel();decoded=[]
    def sound(path):
        value=SimpleNamespace(path=path);decoded.append(path);return value
    mixer=SimpleNamespace(Channel=lambda index:channel,Sound=sound,get_init=lambda:True)
    piano=OpeningPiano(mixer,Executor,lambda values:None)
    piano.start(.4,paths=['one','three','seven'])
    assert decoded==['seven','three'] and channel.current.path=='seven'
    piano.update(.3);assert channel.queued.path=='three'
    channel.current,channel.queued=channel.queued,None
    piano.update(.3);assert decoded==['seven','three','one']
    assert piano.current.path=='three' and piano.queued is None
    executor=piano.executor;piano.update(.3,encounter=True)
    assert channel.current is None and channel.queued is None and executor.closed
    piano.update(.3);assert channel.current is None


def test_reopening_does_not_immediately_repeat_last_selected_chapter():
    channel=Channel();mixer=SimpleNamespace(Channel=lambda index:channel,Sound=lambda path:SimpleNamespace(path=path),get_init=lambda:True)
    piano=OpeningPiano(mixer,Executor,lambda values:None)
    piano.paths=['one','three'];piano.last_path='three'
    assert piano._next_path()=='one'
    assert piano._next_path()=='three'
    assert piano._next_path()=='one'
