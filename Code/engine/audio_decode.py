"""Decode compressed audio without taking SDL_mixer's playback lock.

Mix_LoadMusic_RW holds Mix_LockAudio while decoding an entire OGG/MP3 chunk.
A worker thread alone therefore cannot protect the playing boot recording.
libsndfile decodes independently; SDL receives PCM, preserving its own format
conversion and channel routing. Owner-selected WAV cues keep the original path.
"""
import io
import os
import wave
import pygame


def load_sound(path, *, mixer=None):
    mixer=pygame.mixer if mixer is None else mixer
    if not isinstance(path,(str,os.PathLike)) or not os.path.isfile(path) or os.path.splitext(path)[1].lower() not in ('.ogg','.mp3'):
        return mixer.Sound(path)
    import soundfile
    with soundfile.SoundFile(str(path)) as source:
        rate=source.samplerate;channels=source.channels
        # MP3 containers can overestimate frame count. Array reads trim to the
        # actual decoded length instead of asserting that the estimate is exact.
        pcm=source.read(dtype='int16',always_2d=True).tobytes()
    if mixer.get_init()==(rate,-16,channels):
        return mixer.Sound(buffer=pcm)
    # SDL_LoadWAV's format conversion does not enter Mix_LoadMusic_RW. Preserve
    # SDL's resampling/channel behavior for mono or non-44100Hz source assets.
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as target:
        target.setnchannels(channels);target.setsampwidth(2);target.setframerate(rate)
        target.writeframes(pcm)
    buffer.seek(0)
    return mixer.Sound(file=buffer)
