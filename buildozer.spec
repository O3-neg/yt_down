[app]
title = YouTube Downloader
package.name = youtubedownloader
package.domain = org.ytdl
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 2.0

# Dependências (versões testadas)
requirements = python3,kivy==2.2.1,android,yt-dlp,certifi,brotli,mutagen,pycryptodomex,websockets,urllib3,charset-normalizer

orientation = portrait
fullscreen = 0

# Permissões Android
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.arch = armeabi-v7a

# Evita problemas com SSL
android.add_src = 

# Bootstrap
p4a.bootstrap = sdl2

# Força rebuild
android.gradle_dependencies = 

# Configurações extras
android.presplash_color = #FFFFFF
android.enable_androidx = True

# NDK
android.ndk_api = 21

[buildozer]
log_level = 2
warn_on_root = 1
