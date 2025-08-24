[app]

android.sdk_path = $HOME/android-sdk
android.ndk_path = $HOME/android-sdk/ndk/25.1.8937393
android.build_tools = 33.0.2

# (str) Title of your application
title = Neon Dash

# (str) Package name
package.name = neondash

# (str) Package domain (must be unique)
package.domain = org.njstr

# (str) Source code where main.py is located
source.dir = .

# (str) Main .py file
source.main = main.py

# (str) Application versioning
version = 0.1

# (str) Full version string
version.full = 0.1.0

# (str) Application requirements
# Add libraries your game needs (pygame, kivy, etc.)
requirements = python3, kivy

# (str) Presplash of the application
presplash.filename = %(source.dir)s/assets/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/icon.png

# (list) Permissions your app needs
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (bool) Indicate if the application should be fullscreen
fullscreen = 1

# (str) Supported orientations
orientation = landscape

# (str) The format used to package the app for Android
# Default is apk, but aab is supported if you want Play Store
android.format = apk

# (list) Application entry point(s)
# Keep default
entrypoint = main.py

# (str) Application theme (for modern Android look)
android.theme = @android:style/Theme.DeviceDefault.NoActionBar.Fullscreen

# (list) Java .jar files to add
android.add_jars =

# (list) Python files to include
source.include_exts = py,png,jpg,kv,atlas

# (list) Assets to include (icons, sounds, fonts, etc.)
source.include_patterns = assets/*

# (bool) Indicate if you want to copy all files from source.dir
copy_data = 1

# (str) Android API level
android.api = 33

# (str) Minimum API your app supports
android.minapi = 21

# (str) Android SDK directory (set in build.yml)
sdk.dir = $HOME/android-sdk

# (str) Android NDK directory (set in build.yml)
ndk.dir = $HOME/android-sdk/ndk/25.1.8937393

# (bool) Use SDL2 (better for games)
window = sdl2

# (str) Logcat filters
log_level = 2

# (bool) Hide the keyboard on start
android.hide_keyboard = 1

# (bool) Enable hardware acceleration (important for games)
android.enable_accelerometer = 1
android.enable_multiprocess = 1

# (str) Application category
category = Game

# (bool) Package as release or debug (default is debug)
# Set this to 1 for release builds
release = 0
