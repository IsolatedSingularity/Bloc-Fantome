# Local music files

This directory intentionally contains no audio. Keep actual recordings in a local, non-repository media directory, then fill the corresponding `local_path` in a local copy of `audio/manifest.json`. Keep title, composer, recording artist/version, original source and acquisition notes together. Do not rename a text placeholder to an audio extension.

Use the original file extension. A `.flac`, `.mp3`, `.wav` or `.ogg` filename is not evidence that the decoder or loop transition works; test the actual file with Bloc's current backend. Keep the original master unchanged. Put derived loop/crossfade edits in a separate directory with source and edit notes.

`loop_start_seconds` and `loop_end_seconds` remain null until auditioned. Do not infer seamless looping from a soundtrack title or automatically trim a piano's quiet attack/decay as “silence.” Start by playing the original beginning-to-end.

For scale: three minutes of 44.1 kHz stereo signed-16-bit decoded audio occupies 31,752,000 bytes, about 30.28 MiB before object overhead. The current backend has both a current track and preload/sequence paths; total memory is not always one compressed file. Keep decoded selections bounded. [Backend](../../SOURCES.md#b-audio), [checked calculation](../../qa/arithmetic.json).

The kit does not alter any repository ignore rules, copy files into the game, or upload recordings.
