# Peacock / Skyshowtime for Kodi

**This addon is under development and not all may work correctly.**

## Important notes: ##
- Login by entering username and password is not possible yet. It's necessary to get the cookie from a web browser. You'll find below some methods to do it.
- ~~Skyshowtime doesn't work yet ([see this](https://github.com/Paco8/plugin.video.skyott/issues/3)).~~
- Due to the DRM this platform use, playback only works on Android devices.

My intention was to develop an addon for Skyshowtime, but since I don't know how to generate the header signatures and Peacock uses the same API (and in this case the key for the header signatures is known), I ended up creating an addon for Peacock. I'm not even subscribed to Peacock, I created an account and fortunately they allow to play some videos without a subscription.

## How to get the cookie ##
This tool can extract automatically the cookie from a web browser:
https://github.com/Paco8/SkyExtractCookie

## How to get the cookie manually
If the above tool doesn't work for you, you can try to get it manually:
- In Chrome open the development tools (Ctrl + Shift + I).
- Select the **Network** tab.
- In the field in the top left (the filter) type `watch/home`.
- Now open https://www.peacocktv.com/watch/home (or https://www.skyshowtime.com/watch/home).
- When it gets loaded you'll see the file `home` in the development tools. Click on it.
- Select the the **Headers** tab on the right panel.
- Scroll down until you see the request header, you'll find the cookie there.
- Right click on it and select "copy value".
- Paste the cookie in a text editor and save the file with the name "cookie.conf".
- Copy the file anywhere in the Android device (for example the Download folder). Then go to the Accounts option in the addon and select "Login with a cookie file" and select the file you previously copied to the device.
