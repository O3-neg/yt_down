[app]
title = YouTube Downloader
package.name = youtubedownloader
package.domain = org.ytdl
source.dir = .
source.include_exts = py
version = 2.0
requirements = python3,kivy,yt-dlp,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 31
android.minapi = 21
android.ndk = 23b
android.arch = armeabi-v7a
android.gradle_dependencies = 
android.enable_androidx = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
