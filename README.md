![Kodi version](https://img.shields.io/badge/kodi%20versions-19--21-blue)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/Paco8/plugin.video.skyott)
![GitHub all releases](https://img.shields.io/github/downloads/Paco8/plugin.video.skyott/total)

# Skyshowtime addon for Kodi

## Important note: ##
**Playback only works on Android devices (including firesticks) due to DRM restrictions.**

## Installation
### Manual installation
You can download the package from the [Releases page](https://github.com/Paco8/plugin.video.skyott/releases).

### Installation via Repository
- Add this URL as a source in Kodi: `https://paco8.github.io/kodi-repo/`
- In Add-ons, select the option _Install from zip file_ and install the package **repository.spain** from the source you just added.
- Now, in _Install from repository_, go to _Spain OTT repository_, Video Add-ons, and install **SkyOtt**.

## Important note about login: ##
The option to log in using a username and password has been removed because it seems the method used by the addon is occasionally flagged as suspicious by the server and after a couple of days they will close your session and ask you to reset your password. You can use the following application for Android to get a key file that you can use to log in: https://github.com/Paco8/SkyExtractCookieAndroid

<!--
## Select the streaming service
Open the settings of the addon and select whether to use PeacockTV or SkyShowtime.
-->

<!--
## How to get the cookie ##
This application for Android can extract automatically the cookie:
https://github.com/Paco8/SkyExtractCookieAndroid
<br>
There's also a similar application for PC:
https://github.com/Paco8/SkyExtractCookie
-->
<!--
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
-->
## Settings
### Main
<!-- - **Streaming service**: Select PeacockTV or SkyShowtime. -->
- **Remember username and password**: if this option is enabled the addon will save your login credentials in the disk.
- **Subscription country**: (**optional**) two-letter code (such as `ES` `PT` `NL`) of the subscription country.
- **Preferred server**: Videos are hosted in different servers. You can choose the one which works better for you.
- **Enable 4K**: Enables 4K content. Playback may not work on non 4K devices.
- **Enable HDCP**: Users of Android devices with Widevine L3 may need to turn it off.
- **Send video progress to provider's server**: the stream positions will be sent to the server so that you can resume playback in other applications.
- **Update interval**: the time interval, in seconds, between video progress updates.
- **Show only subscribed content**: Only titles included in your subscription will be displayed.
- **Configure InputStream Adaptive**: Opens the settings of InputStream Adaptive.
## Subtitles
- **Improved subtitles**: Subtitles will be downloaded prior to playback and converted to the more customizable SSA/ASS format.
- **Improved subtitles settings**: Opens a new configuration window that allows you to customize the appearance of subtitles.
- **Use only for these languages**: Only the subtitles for the specified languages (two letter language codes, separated by spaces) will be downloaded. For example: `es en pl` will download subtitles in Spanish, English and Polish.
### Proxy
- **Manifest alteration**: Allows the addon to perform some changes in the manifest.
- **Fix audio and subtitle language names**: Versions 18 and 19 of Kodi don't support language codes that include a country code (such as `es-ES`). As a workaround, this option removes the country code.
- **Exclude DD+ audio tracks**: The addon will remove any audio tracks in DD+ format.
- **Exclude AAC audio tracks**: The addon will remove any audio tracks in AAC format.

## Donation
If you find this addon useful there's now the possibility to **[buy me a coffee](https://www.buymeacoffee.com/addons)**.
