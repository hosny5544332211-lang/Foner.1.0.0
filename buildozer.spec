[app]
title = Cyber Doom 3D
package.name = cyberdoom3d
package.domain = org.game
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
icon.filename = %(source.dir)s/icon.png.jpg

requirements = python3,pygame,sdl2,sdl2_image,sdl2_mixer,sdl2_ttf

orientation = landscape
fullscreen = 1

android.permissions = VIBRATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
