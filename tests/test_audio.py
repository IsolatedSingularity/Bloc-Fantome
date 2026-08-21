import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audio_module", ROOT / "Code" / "engine" / "audio.py")
AUDIO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIO)


class FakeChannel:
    def __init__(self, index):
        self.index = index
        self.busy = False
        self.volume = None
        self.played = []
        self.stops = 0
        self.end_event = 0
        self.paused = False

    def get_busy(self):
        return self.busy

    def set_volume(self, *values):
        self.volume = values

    def play(self, sound, loops=0):
        self.busy = True
        self.played.append((sound, loops))

    def stop(self):
        self.busy = False
        self.stops += 1

    def set_endevent(self, event_type):
        self.end_event = event_type

    def pause(self):
        self.paused = True

    def unpause(self):
        self.paused = False


class FakeSound:
    def __init__(self, path):
        self.path = path
        self.volume = 0.0

    def set_volume(self, volume):
        self.volume = volume


class FakeMixer:
    def __init__(self):
        self.channels = {}

    def Channel(self, index):
        return self.channels.setdefault(index, FakeChannel(index))

    def Sound(self, path):
        return FakeSound(path)


class FakeMusic:
    def __init__(self):
        self.busy = False
        self.loaded = []
        self.play_count = 0
        self.stop_count = 0
        self.volume = 0.0

    def get_busy(self):
        return self.busy

    def load(self, path):
        self.loaded.append(path)

    def play(self):
        self.busy = True
        self.play_count += 1

    def stop(self):
        self.busy = False
        self.stop_count += 1

    def set_volume(self, volume):
        self.volume = volume


class AudioRouterTests(unittest.TestCase):
    def test_gain_is_clamped_with_headroom(self):
        mixer = FakeMixer()
        router = AUDIO.AudioRouter(mixer, {"effects": (0,)}, peak_headroom=0.7)
        channel = router.play(object(), volume=4.0)
        self.assertEqual(channel.volume, (0.7, 0.7))

    def test_busy_pool_drops_overlap_unless_replacement_is_requested(self):
        mixer = FakeMixer()
        router = AUDIO.AudioRouter(mixer, {"effects": (0,)})
        first = router.play("first")
        self.assertIsNone(router.play("second"))
        replacement = router.play("second", replace=True)
        self.assertIs(first, replacement)
        self.assertEqual(replacement.played[-1], ("second", 0))

    def test_groups_do_not_steal_each_others_channels(self):
        mixer = FakeMixer()
        router = AUDIO.AudioRouter(mixer, {"effects": (0,), "ambient": (1,)})
        effects = router.play("place", group="effects")
        ambient = router.play("cave", group="ambient")
        self.assertNotEqual(effects.index, ambient.index)

    def test_preloaded_music_backend_decodes_one_track_on_reserved_channel(self):
        mixer = FakeMixer()
        backend = AUDIO.PreloadedMusicBackend(mixer, channel_index=31)
        backend.set_endevent(42)
        backend.load("calm.ogg")
        backend.set_volume(0.4)
        backend.play()
        self.assertTrue(backend.get_busy())
        self.assertEqual(mixer.channels[31].end_event, 42)
        self.assertEqual(mixer.channels[31].played[-1][0].path, "calm.ogg")
        self.assertEqual(mixer.channels[31].volume, (0.4,))

    def test_preloaded_explicit_stop_restores_but_does_not_use_end_event(self):
        mixer = FakeMixer()
        backend = AUDIO.PreloadedMusicBackend(mixer, channel_index=31)
        backend.set_endevent(42)
        backend.load("calm.ogg")
        backend.play()
        backend.stop()
        self.assertFalse(backend.stop_posts_end_event)
        self.assertEqual(mixer.channels[31].end_event, 42)
        self.assertFalse(backend.get_busy())


class MusicControllerTests(unittest.TestCase):
    def test_immediate_dimension_replacement_has_no_silent_pending_state(self):
        music = FakeMusic()
        controller = AUDIO.MusicController(music, shuffle=lambda tracks: None)
        controller.set_playlist(["overworld.ogg"], fade=False)
        controller.set_playlist(["nether.ogg"], fade=False)
        self.assertEqual(music.loaded[-1], "nether.ogg")
        self.assertTrue(music.get_busy())
        self.assertFalse(controller.fading_out)
        self.assertIsNone(controller.pending_tracks)

    def test_expected_stop_event_does_not_skip_new_dimension_track(self):
        music = FakeMusic()
        controller = AUDIO.MusicController(music, shuffle=lambda tracks: None)
        controller.set_playlist(["overworld.ogg"], fade=False)
        controller.set_playlist(["nether-a.ogg", "nether-b.ogg"], fade=True)

        controller.update(controller.fade_out_ms)
        self.assertEqual(music.loaded[-1], "nether-a.ogg")
        self.assertEqual(music.play_count, 2)

        self.assertFalse(controller.handle_end_event())
        self.assertEqual(music.loaded[-1], "nether-a.ogg")
        self.assertEqual(music.play_count, 2)

    def test_natural_end_event_advances_playlist(self):
        music = FakeMusic()
        controller = AUDIO.MusicController(music, shuffle=lambda tracks: None)
        controller.set_playlist(["one.ogg", "two.ogg"], fade=False)

        self.assertTrue(controller.handle_end_event())
        self.assertEqual(music.loaded, ["one.ogg", "two.ogg"])

    def test_persisted_last_track_is_not_repeated_first(self):
        music = FakeMusic()
        controller = AUDIO.MusicController(music, shuffle=lambda tracks: None)
        controller.last_track = r"old-launch\one.ogg"
        controller.set_playlist([
            r"new-launch\one.ogg", r"new-launch\two.ogg"
        ], fade=False)
        self.assertEqual(music.loaded[-1], r"new-launch\two.ogg")

    def test_playlist_reshuffles_after_a_complete_cycle(self):
        music = FakeMusic()
        shuffles = []
        controller = AUDIO.MusicController(
            music, shuffle=lambda tracks: shuffles.append(tuple(tracks))
        )
        controller.set_playlist(["one.ogg", "two.ogg"], fade=False)
        controller.handle_end_event()
        controller.handle_end_event()
        self.assertEqual(len(shuffles), 2)
        self.assertEqual(len(music.loaded), 3)

    def test_music_volume_is_clamped(self):
        music = FakeMusic()
        controller = AUDIO.MusicController(music)
        controller.set_volume(4)
        self.assertEqual(music.volume, 0.82)

    def test_music_headroom_applies_during_fade_and_steady_playback(self):
        music = FakeMusic()
        controller = AUDIO.MusicController(
            music, volume=0.5, output_headroom=0.8, shuffle=lambda tracks: None
        )
        controller.set_playlist(["one.ogg"], fade=False)
        controller.update(controller.fade_in_ms)
        self.assertAlmostEqual(music.volume, 0.4)


if __name__ == "__main__":
    unittest.main()
