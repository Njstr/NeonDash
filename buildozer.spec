[app]
# (str) Title of your application
title = Neon Dash

# (str) Package name (must be unique on Android)
package.name = neondash

# (str) Package domain (used for Android/iOS)
package.domain = org.njstr

# (str) Source code where main.py lives
source.dir = .

# (str) Main script
source.main = neon_dash.py

# (list) Permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE

# (str) Application version
version = 1.0.0

# (str) Application version code (integer)
version.code = 1

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Application requirements
# Add pygame + any dependencies
requirements = python3, pygame

# (str) Icon (optional)
# icon.filename = %(source.dir)s/icon.png

# (str) Supported architectures (armeabi-v7a = 32-bit, arm64-v8a = 64-bit)
android.archs = arm64-v8a, armeabi-v7a

# (bool) Enable logcat
log_level = 2

# (bool) Copy library instead of symlink
copy_libs = 1


[buildozer]
# (str) Log level (0 = error only, 2 = debug, 1 = normal)
log_level = 2

# (str) Output directory for build artifacts
build_dir = .buildozer

# (str) Path to store the final APK
bin_dir = bin

# (str) Android NDK API version
android.api = 33

# (str) Android NDK (for compiling)
android.ndk = 25b

# (str) Android SDK version
android.sdk = 33

# (int) Screen orientation
orientation = portrait

# (bool) Automatically accept SDK licenses
android.accept_sdk_license = True
