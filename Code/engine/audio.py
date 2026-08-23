"""Bounded music and sound-effect routing for Bloc Fantôme."""

from collections import defaultdict
import os
import random
from typing import Any, Callable, Dict, Iterable, Optional, Sequence


class PreloadedMusicBackend:
    """Pygame music-like API backed by one fully decoded ``Sound``.

    ``pygame.mixer.music`` streams through SDL_mixer's decoder while the app is
    running.  Keeping one decoded track on a reserved channel removes decoder
    chunk boundaries and disk access from steady playback.  Only the current
    track is retained, so memory use is bounded by one decoded song.
    """

    def __init__(self, mixer: Any, channel_index: int = 31,
                 logger: Optional[Callable[[str], None]] = None) -> None:
        self._mixer = mixer
        self._channel = mixer.Channel(int(channel_index))
        self._logger = logger or (lambda _message: None)
        self._sound = None
        self._path: Optional[str] = None
        self._volume = 1.0
        self._end_event = 0
        self._preloaded: Dict[str, Any] = {}
        self.stop_posts_end_event = False

    def preload(self, path: str) -> None:
        """Decode a bounded startup track without replacing current playback."""
        path = str(path)
        if path == self._path or path in self._preloaded:
            return
        self._preloaded[path] = self._mixer.Sound(path)
        self._preloaded[path].set_volume(self._volume)
        while len(self._preloaded) > 3:
            self._preloaded.pop(next(iter(self._preloaded)))

    def load(self, path: str) -> None:
        self.stop()
        path = str(path)
        if self._sound is not None and self._path:
            self._preloaded[self._path] = self._sound
        self._sound = self._preloaded.pop(path, None)
        if self._sound is None:
            self._sound = self._mixer.Sound(path)
        self._path = path
        self._sound.set_volume(self._volume)
        self._logger(f"Music decoded: {os.path.basename(self._path)}")

    def play(self) -> None:
        if self._sound is None:
            raise RuntimeError("No decoded music track is loaded")
        self._channel.set_volume(self._volume)
        self._channel.play(self._sound)

    def stop(self) -> None:
        # Channel.stop can post its configured end event on some SDL_mixer
        # builds. Explicit stops are transitions, not natural track endings.
        self._channel.set_endevent(0)
        self._channel.stop()
        self._channel.set_endevent(self._end_event)

    def pause(self) -> None:
        self._channel.pause()

    def unpause(self) -> None:
        self._channel.unpause()

    def get_busy(self) -> bool:
        return bool(self._channel.get_busy())

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, float(volume)))
        self._channel.set_volume(self._volume)

    def set_endevent(self, event_type: int = 0) -> None:
        self._end_event = int(event_type)
        self._channel.set_endevent(self._end_event)

    @property
    def path(self) -> Optional[str]:
        return self._path


DEFAULT_CHANNEL_GROUPS: Dict[str, Sequence[int]] = {
    "ui": (0, 1),
    "weather": (2, 3),
    "ambient": (4, 5, 6, 7),
    "effects": tuple(range(8, 24)),
    "horror": (24, 25),
    "portal": (26,),
}


class AudioRouter:
    """Route sounds through small, named channel pools with safe headroom."""

    def __init__(
        self,
        mixer: Any,
        channel_groups: Optional[Dict[str, Iterable[int]]] = None,
        peak_headroom: float = 0.72,
    ) -> None:
        self._mixer = mixer
        groups = channel_groups or DEFAULT_CHANNEL_GROUPS
        self._groups = {
            name: tuple(mixer.Channel(index) for index in indices)
            for name, indices in groups.items()
        }
        self._cursor = defaultdict(int)
        self._group_volume = defaultdict(lambda: 1.0)
        self.peak_headroom = self._clamp(peak_headroom)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def set_group_volume(self, group: str, volume: float) -> None:
        self._group_volume[group] = self._clamp(volume)

    def play(
        self,
        sound: Any,
        *,
        group: str = "effects",
        volume: float = 1.0,
        pan: float = 0.0,
        loops: int = 0,
        replace: bool = False,
    ) -> Optional[Any]:
        """Play a sound without allowing unbounded overlap or clipped gain."""

        if sound is None:
            return None
        channels = self._groups.get(group) or self._groups["effects"]
        channel = next((candidate for candidate in channels if not candidate.get_busy()), None)
        if channel is None:
            if not replace:
                return None
            index = self._cursor[group] % len(channels)
            channel = channels[index]
            self._cursor[group] = index + 1
            channel.stop()

        gain = self._clamp(volume) * self._group_volume[group] * self.peak_headroom
        pan = max(-1.0, min(1.0, float(pan)))
        left = gain * (1.0 if pan <= 0.0 else 1.0 - pan)
        right = gain * (1.0 if pan >= 0.0 else 1.0 + pan)
        channel.set_volume(self._clamp(left), self._clamp(right))
        channel.play(sound, loops=loops)
        return channel

    def stop_group(self, group: str) -> None:
        for channel in self._groups.get(group, ()):
            channel.stop()


class MusicController:
    """Own the single music backend and its dimension transitions.

    Pygame posts the configured end event for both natural completion and an
    explicit ``stop``.  Without remembering the expected stop, a dimension
    fade can advance the newly-started playlist twice.  This controller keeps
    that state in one place and suppresses only the event caused by its own
    transition stop.
    """

    def __init__(
        self,
        music: Any,
        *,
        volume: float = 0.3,
        fade_in_ms: int = 1500,
        fade_out_ms: int = 1200,
        output_headroom: float = 0.82,
        shuffle: Optional[Callable[[list], None]] = None,
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._music = music
        self._shuffle = shuffle or random.shuffle
        self._logger = logger or (lambda _message: None)
        self.volume = self._clamp(volume)
        self.output_headroom = self._clamp(output_headroom)
        self.fade_in_ms = max(1, int(fade_in_ms))
        self.fade_out_ms = max(1, int(fade_out_ms))
        self.tracks: list[str] = []
        self.index = 0
        self.pending_tracks: Optional[list[str]] = None
        self.fade_elapsed_ms = 0.0
        self.fading_in = False
        self.fading_out = False
        self._expected_stop_events = 0
        self.last_track: Optional[str] = None

    def set_endevent(self, event_type: int) -> None:
        """Configure natural track completion on either supported backend."""
        self._music.set_endevent(int(event_type))

    def pause(self) -> None:
        self._music.pause()

    def unpause(self) -> None:
        self._music.unpause()

    def get_busy(self) -> bool:
        return bool(self._music.get_busy())

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def set_volume(self, volume: float) -> None:
        self.volume = self._clamp(volume)
        if not self.fading_in and not self.fading_out:
            self._music.set_volume(self._gain())

    def _gain(self, scale: float = 1.0) -> float:
        """Leave mix-bus headroom for effects and speaker enhancement paths."""
        return self._clamp(self.volume * self.output_headroom * scale)

    def set_playlist(self, tracks: Iterable[str], *, fade: bool = True) -> bool:
        """Shuffle and activate a playlist, fading the old one when possible."""

        playlist = list(dict.fromkeys(str(track) for track in tracks if track))
        if not playlist:
            return False
        self._shuffle(playlist)
        self._avoid_immediate_repeat(playlist)
        if fade and self._music.get_busy():
            self.pending_tracks = playlist
            self.fade_elapsed_ms = 0.0
            self.fading_in = False
            self.fading_out = True
            return True
        self._activate(playlist)
        return True

    def _activate(self, tracks: list[str]) -> None:
        self.tracks = tracks
        self.index = 0
        self.pending_tracks = None
        self.fading_out = False
        self.play_next()

    def _avoid_immediate_repeat(self, tracks: list[str]) -> None:
        if (
            len(tracks) > 1
            and self.last_track
            and os.path.basename(tracks[0]) == os.path.basename(self.last_track)
        ):
            tracks[0], tracks[1] = tracks[1], tracks[0]

    def play_next(self) -> bool:
        """Start the next playable track and begin a short fade-in."""

        if not self.tracks:
            return False
        attempts = len(self.tracks)
        while attempts:
            if self.index >= len(self.tracks):
                self._shuffle(self.tracks)
                self._avoid_immediate_repeat(self.tracks)
                self.index = 0
            selected = self.tracks[self.index]
            self.index += 1
            attempts -= 1
            try:
                self._music.load(selected)
                self._music.set_volume(0.0)
                self._music.play()
            except Exception as exc:
                self._logger(f"Could not play music: {exc}")
                continue
            self.fade_elapsed_ms = 0.0
            self.fading_out = False
            self.fading_in = True
            self.last_track = selected
            self._logger(f"Now playing: {os.path.basename(selected)}")
            return True
        return False

    def handle_end_event(self) -> bool:
        """Handle a Pygame music-end event.

        Returns ``True`` only when the event advanced the playlist.
        """

        if self._expected_stop_events:
            self._expected_stop_events -= 1
            return False
        if self.fading_out:
            return False
        return self.play_next()

    def update(self, elapsed_ms: float) -> None:
        if self.fading_out:
            self.fade_elapsed_ms += elapsed_ms
            progress = min(1.0, self.fade_elapsed_ms / self.fade_out_ms)
            self._music.set_volume(self._gain(1.0 - progress))
            if progress >= 1.0:
                self.fading_out = False
                if getattr(self._music, "stop_posts_end_event", True):
                    self._expected_stop_events += 1
                self._music.stop()
                if self.pending_tracks:
                    self._activate(self.pending_tracks)
            return

        if self.fading_in:
            self.fade_elapsed_ms += elapsed_ms
            progress = min(1.0, self.fade_elapsed_ms / self.fade_in_ms)
            self._music.set_volume(self._gain(progress * progress))
            if progress >= 1.0:
                self.fading_in = False
                self._music.set_volume(self._gain())

    def stop(self) -> None:
        self.pending_tracks = None
        self.fading_in = False
        self.fading_out = False
        self._music.stop()
