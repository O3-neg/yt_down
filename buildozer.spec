[app]
title = YouTube Downloader
package.name = youtubedownloader
package.domain = org.ytdl
source.dir = .
source.include_exts = py
version = 2.0
requirements = python3==3.11.6,kivy==2.3.0,yt-dlp,android,certifi,brotli,mutagen,pycryptodomex,websockets
orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.arch = armeabi-v7a

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
