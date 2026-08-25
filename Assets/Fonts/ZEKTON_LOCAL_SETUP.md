# Zekton local asset

Bloc Fantome uses `Assets/Fonts/Zekton/Zekton-Regular.otf` for its runtime UI.
The repository owner supplies this file under their separate application/game
license. The font software and the private license records are intentionally
excluded from Git.

To restore the local asset, extract the owner's `zekton.zip` into
`Assets/Fonts/Zekton/`. The directory should contain `Zekton-Regular.otf`.
The application falls back to Pygame's default font when the licensed local
asset is unavailable, so source checkouts remain runnable.
