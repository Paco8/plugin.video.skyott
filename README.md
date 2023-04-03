![Kodi version](https://img.shields.io/badge/kodi%20versions-18--19--20-blue)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/Paco8/plugin.video.skyott)
![GitHub all releases](https://img.shields.io/github/downloads/Paco8/plugin.video.skyott/total)

# Peacock / Skyshowtime for Kodi

**This addon is under development and not all may work correctly.**

## Important notes: ##
-  Logging in by entering a username and password is not possible yet. For the moment it's necessary to get a cookie from a web browser. You'll find below some methods to do it.
- Playback is only supported on Android devices (including firesticks) due to DRM restrictions.

## Select the streaming service
Open the settings of the addon and select whether to use PeacockTV or SkyShowtime.

## How to get the cookie ##
This application for Android can extract automatically the cookie:
https://github.com/Paco8/SkyExtractCookieAndroid
<br>
There's also a similar application for PC:
https://github.com/Paco8/SkyExtractCookie

## How to get the cookie manually
If the above tools don't work for you, you can try to get it manually:
- In Chrome open the development tools (Ctrl + Shift + I).
- Select the **Network** tab.
- In the field in the top left (the filter) type `watch/home`.
- Now open https://www.peacocktv.com/watch/home or https://www.skyshowtime.com/watch/home.
- When it gets loaded you'll see the file `home` in the development tools. Click on it.
- Select the the **Headers** tab on the right panel.
- Scroll down until you see the request header, you'll find the cookie there.
- Right click on it and select "copy value".
- Paste the cookie in a text editor and save the file with the name "cookie.conf".
- Copy the file anywhere in the Android device (for example the Download folder). Then go to the Accounts option in the addon and select "Login with a cookie file" and select the file you previously copied to the device.

## Donation
If you find this addon useful there's now the possibility to **[buy me a coffee](https://www.buymeacoffee.com/paco8.addons)**.
