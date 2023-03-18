# Peacock / Skyshowtime for Kodi

**This addon is under development and is barely usable. Login doesn't work.**

You can select Peacock or SkyShowtime in the addon settings.

In order to login you need to get the cookie from a web browser and copy it to `userdata/addon_data/plugin.video.skyott/peacocktv` with the name `cookie.conf`.

After that you need to select a profile before trying to play a video. Due to the DRM this platform use, playback only works on Android devices.

Skyshowtime doesn't work because I don't know the key to generate the header signatures.

**Note:** my intention was to develop an addon for Skyshowtime, but since I don't know how to generate the header signatures and Peacock uses the same API (and in this case the key for the header signatures is known), I ended up creating an addon for Peacock. I'm not even subscribed to Peacock, I created an account and fortunately they allow to play some videos without a subscription. I'm not even in the US, so I had to use free proxies to access Peacock. However, these proxies are very slow and often don't work at all, which makes it difficult for me to even play those videos.

## How to get the cookie ##
This tool can extract automatically the cookie from a web browser:
https://github.com/Paco8/SkyExtractCookie

## How to get the cookie manually
If the above tool doesn't work for you, you can try to get it manually:
- In Chrome open the development tools (Ctrl + Shift + I).
- Select the **Network** tab.
- In the field in the top left (the filter) type `watch/home`.
- Now open https://www.peacocktv.com/watch/home.
- When it gets loaded you'll see the file `home` in the development tools. Click on it.
- Select the the **Headers** tab on the right panel.
- Scroll down until you see the request header, you'll find the cookie there.
- Right click on it and select "copy value".
- Paste the cookie in a text editor and save the file with the name "cookie.conf".
- Copy the file in the folder `userdata/addon_data/plugin.video.skyott/peacocktv` in Kodi (the full path may be something like `/Android/data/org.xbmc.kodi/files/.kodi/userdata/addon_data/plugin.video.skyott/peacocktv`).
