#!/usr/bin/env python
# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import json
import requests
try:
    # Python 3
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
except ImportError:
    # Python 2
    from urlparse import urlparse, urlunparse, parse_qs
    from urllib import urlencode

def get_fw_data(profile_id, playback_info, account, territory, headers, platform):
  freewheel = playback_info['response']['thirdParties']['FREEWHEEL']
  if 'durationMs' in playback_info['response']:
    duration = str(int(playback_info['response']['durationMs'] / 1000))
  else:
    duration = "600"

  stream_type = 'linear' if 'serviceKey' in playback_info['response'] else 'vod'

  query = {
    "appName": "skyshowtime",
    "appBuild": "65f0ee2",
    "deviceAdvertisingIdType": "dpid",
    "obfuscatedFreewheelPersonaId": account['freewheel'],
    "sdkName": "core-video-sdk-js",
    "sdkVersion": "7.0.0",
    "playerVersion": "v3.3.10-v64",
    "isMiniPlayer": "false",
    "adServerContentId": freewheel['contentId'],
    "cdnName": playback_info['cdn'],
    "mvpdHash": "D2C",
    "coppaApplies": "false",
    "territory": territory,
    "isBingeViewing": "false",
    "serviceProfileid": profile_id,
    "httpUserAgent": headers['User-Agent'],
    "videoDurationInSeconds": duration,
    "slePreRoll": "false",
    "isPrefetch": "true",
    "streamType": stream_type,
    "streamSubType": "movie",
    "audioLanguage": "en",
    "subtitleLanguage": "off",
    "brightlineEnabled": "false",
    "frameAdsEnabled": "false",
    "adCompatibilityEncodingProfile": freewheel['adCompatibilityEncodingProfile'],
    "accountSegment": '|'.join(account['account_type']),
    "contentSegment": '|'.join(account['my_segments']),
    "personaSegment": "STANDARD",
    "obfuscatedFreewheelProfileId": freewheel['userId'],
    "platform": "web",
    "playerName": "sst-web",
    "appVersion": "5.5.12-gsp",
    "playerHeightPixels": "1080",
    "playerWidthPixels": "1920",
    "variantId": "mediatailor",
    "bc": "0"
  }
  url = 'https://video-ads-module-sst.ad-tech.nbcuni.com/v1/freewheel-params'

  if platform != 'SkyShowtime':
    query.update({
        "appName": "peacock",
        "appBuild": "5c90e5a",
        "sdkVersion": "5.1.2-peacock",
        "playerVersion": "v3.3.10-v41.1",
        "playerName": "nbcu-web",
        "appVersion": "5.5.37-gsp",
        "usPrivacy": "1YNN"
    })
    url = 'https://video-ads-module.ad-tech.nbcuni.com/v1/freewheel-params'

  #print(json.dumps(query, indent=4))
  #print(json.dumps(headers, indent=4))

  response = requests.get(url, params=query, headers=headers)
  #print(response.url)
  #print(response.text)
  data = json.loads(response.text)
  return data

def get_ad_url(video_url, fw_data, headers, platform):
  parsed_url = urlparse(video_url)
  original_host = parsed_url.netloc
  query_params = parse_qs(parsed_url.query)
  query_params['mt.config'] = fw_data['mt.config']
  if platform == 'SkyShowtime':
    url = parsed_url.scheme + '://mt.dai-sst.nbcuni.com' + parsed_url.path
  else:
    url = parsed_url.scheme + '://mt.ssai.peacocktv.com' + parsed_url.path
  #print(url)

  ads_params = fw_data['globalParameters'].copy()
  ads_params.update(fw_data['keyValues'])

  post_data = {
    "reportingMode":"client",
    "availSuppression":{
      "mode":"BEHIND_LIVE_EDGE",
      "value":"00:00:00"
    },
    "playerParams":{
      "origin_domain": original_host
    },
    "adsParams": ads_params
  }
  #print(json.dumps(post_data, indent=4))
  #print(json.dumps(query_params, indent=4))

  response = requests.post(url, params=query_params, headers=headers, data=json.dumps(post_data))
  #print(response.text)
  data = json.loads(response.text)
  return data
