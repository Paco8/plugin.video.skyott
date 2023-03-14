# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import sys
import json
import requests
import io
import os
#import time
#import re
#from datetime import datetime

from .log import LOG, print_json
from .network import Network
from .cache import Cache
from .endpoints import Endpoints
from .signature import calculate_signature

class SkyShowtime(object):

    platforms = {
      'skyshowtime': {
         'name': 'SkyShowtime',
         'host': 'skyshowtime.com',
         'config_dir': 'skyshowtime',
         'movies_slug': '/movies/highlights',
         'series_slug': '/entertainment/highlights',
         'headers': {
           'x-skyott-activeterritory': 'ES',
           'x-skyott-client-version': '4.3.12',
           'x-skyott-device': 'COMPUTER',
           'x-skyott-language': 'es-ES',
           'x-skyott-platform': 'PC',
           'x-skyott-proposition': 'SKYSHOWTIME',
           'x-skyott-provider': 'SKYSHOWTIME',
           'x-skyott-territory': 'ES'
         },
      },
      'peacocktv': {
         'name': 'PeacockTV',
         'host': 'peacocktv.com',
         'config_dir': 'peacocktv',
         'movies_slug': '/movies/highlights',
         'series_slug': '/tv/highlights',
         'headers': {
           'x-skyott-activeterritory': 'US',
           'x-skyott-client-version': '4.3.12',
           'x-skyott-device': 'COMPUTER',
           'x-skyott-language': 'en',
           'x-skyott-platform': 'PC',
           'x-skyott-proposition': 'NBCUOTT',
           'x-skyott-provider': 'NBCU',
           'x-skyott-territory': 'US'
         }
      }
    }

    account = {'username': None, 'password': None, 'device_id': None, 'profile_id': None, 'cookie': None, 'user_token': None}

    def __init__(self, config_directory, platform='skyshowtime'):
      self.logged = False

      self.platform = self.platforms[platform]
      self.pldir = self.platform['config_dir']
      if not os.path.exists(config_directory + self.pldir):
        os.makedirs(config_directory + self.pldir)

      # Network
      default_headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
      }
      self.net = Network()
      self.net.headers = default_headers

      # Cache
      self.cache = Cache(config_directory)
      if not os.path.exists(config_directory + 'cache'):
        os.makedirs(config_directory + 'cache')

      # Endpoints
      self.endpoints = Endpoints(self.platform['host']).endpoints

      # Load cookie
      content = self.cache.load_file(self.pldir + '/cookie.conf')
      if content:
        self.account['cookie'] = content.strip()
        self.logged = True

      # Load device_id
      content = self.cache.load_file(self.pldir + '/device_id.conf')
      if content:
        self.platform['device_id'] = content
      else:
        self.platform['device_id'] = self.create_device_id()
        self.cache.save_file(self.pldir + '/device_id.conf', self.platform['device_id'])

      # Load localisation
      localisation_filename = self.pldir + '/localisation.json'
      content = self.cache.load_file(localisation_filename)
      if content:
        extra_headers = json.loads(content)
      else:
        extra_headers = self.get_localisation()
        if 'headers' in extra_headers:
          self.cache.save_json(localisation_filename, data)
      if extra_headers and 'headers' in extra_headers:
        h = extra_headers['headers']
        self.platform['headers'].update({
             'x-skyott-activeterritory': h.get('x-skyott-activeterritory'),
             'x-skyott-language': h.get('x-skyott-language'),
             'x-skyott-territory': h.get('x-skyott-territory'),
        })
      self.net.headers.update(self.platform['headers'])
      #print_json(self.net.headers)

      # Load profile
      content = self.cache.load_file(self.pldir + '/profile_id.conf')
      if content:
        self.account['profile_id'] = content

      # Load user token
      token_filename = self.pldir + '/token.json'
      content = self.cache.load(token_filename, 60)
      if content:
        data = json.loads(content)
      else:
        data = self.get_tokens()
        if 'userToken' in data:
          self.cache.save_json(token_filename, data)
      if data and 'userToken' in data:
        self.account['user_token'] = data['userToken']

    def get_art(self, images):
      def image_url(url):
        return url.replace('?language', '/400?language')

      art = {'icon': None, 'poster': None, 'fanart': None}
      for i in images:
        if i['type'] == 'titleArt34':
          art['poster'] = image_url(i['url'])
        elif i['type'] == 'nonTitleArt34' and not art['poster']:
          art['poster'] = image_url(i['url'])
        elif i['type'] == 'titleArt169' and not art['poster']:
          art['poster'] = image_url(i['url'])
        elif i['type'] == 'landscape':
          art['fanart'] = image_url(i['url'])
      return art

    def get_genres(self, genres):
      res = []
      for d in genres:
        if 'subgenre' in d and len(d['subgenre']) > 0:
          res.append(d['subgenre'][0]['title'])
      return res

    def parse_catalog(self, data):
      res = []
      for e in data:
        t = {'info':{}, 'art':{}}
        t['id'] = e['id']
        t['slug'] = e['slug']
        t['info']['title'] = e['title']
        if e['type'] == 'CATALOGUE/COLLECTION':
          t['type'] = 'category'
          res.append(t)
        elif e['type'] == 'ASSET/PROGRAMME':
          t['type'] = 'movie'
          t['info']['mediatype'] = 'movie'
          t['info']['year'] = e.get('year')
          t['info']['duration'] = e['duration']['durationSeconds']
          t['info']['mpaa'] = e.get('ottCertificate')
          t['info']['plot'] = e.get('synopsisLong')
          t['art'] = self.get_art(e['images'])
          t['info']['genre'] = self.get_genres(e['genreList'])
          res.append(t)
        elif e['type'] == 'CATALOGUE/SERIES':
          t['type'] = 'series'
          t['info']['mediatype'] = 'tvshow'
          t['info']['mpaa'] = e.get('ottCertificate')
          t['info']['plot'] = e.get('synopsisLong')
          t['art'] = self.get_art(e['images'])
          t['info']['genre'] = self.get_genres(e['genreList'])
          res.append(t)
      return res

    def parse_item(self, data):
      e = data
      att = e['attributes']
      t = {'info':{}, 'art':{}}
      t['id'] = e['id']
      t['slug'] = att['slug']
      t['info']['title'] = att['title']
      t['art'] = self.get_art(att['images'])
      t['info']['genre'] = att['genres']
      if e['type'] == 'CATALOGUE/SEASON':
        t['type'] = 'season'
        t['info']['mediatype'] = 'season'
        t['info']['tvshowtitle'] = att['seriesName']
        t['info']['season'] = att['seasonNumber']
      elif e['type'] == 'ASSET/EPISODE':
        t['type'] = 'movie'
        t['info']['mediatype'] = 'episode'
        t['info']['tvshowtitle'] = att['seriesName']
        t['info']['season'] = att['seasonNumber']
        t['info']['episode'] = att['episodeNumber']
      elif e['type'] == 'ASSET/PROGRAMME':
        t['info']['mediatype'] = 'movie'
        t['info']['year'] = e.get('year')
      if e['type'] in ['ASSET/PROGRAMME', 'ASSET/EPISODE']:
        t['info']['plot'] = att['synopsisLong']
        t['info']['duration'] = att['durationSeconds']
        t['info']['mpaa'] = att.get('ottCertificate')
        t['content_id'] = att.get('nbcuId')
        if 'formats' in att:
          t['content_id'] = att['formats']['HD']['contentId']
        t['provider_variant_id'] = att.get('providerVariantId')
      return t

    def parse_items(self, data):
      res = []
      for e in data:
        t = self.parse_item(e)
        res.append(t)
      return res

    def get_catalog(self, slug):
      url = self.endpoints['section'].format(slug=slug)
      LOG(url)
      data = self.net.load_data(url)
      return self.parse_catalog(data['data']['rail']['items'])

    def get_movie_catalog(self):
      url = self.endpoints['section'].format(slug=self.platform['movies_slug'])
      data = self.net.load_data(url)
      return self.parse_catalog(data['data']['group']['rails'])

    def get_series_catalog(self):
      url = self.endpoints['section'].format(slug=self.platform['series_slug'])
      data = self.net.load_data(url)
      return self.parse_catalog(data['data']['group']['rails'])

    def get_series_info(self, slug):
      url = self.endpoints['get-series'].format(slug=slug)
      #LOG(url)
      data = self.net.load_data(url)
      return self.parse_items(data['relationships']['items']['data'])

    def get_seasons(self, slug):
      return self.get_series_info(slug)

    def get_episodes(self, slug):
      return self.get_series_info(slug)

    def get_video_info(self, slug):
      url = self.endpoints['get-video-info'].format(slug=slug)
      print(url)
      data = self.net.load_data(url)
      #print_json(data)
      #self.cache.save_json('movie.json', data)
      return self.parse_item(data)

    def login(self, username='', password=''):
      url = self.endpoints['login']
      #print(url)
      headers = self.net.headers.copy()
      headers['content-type'] = 'application/x-www-form-urlencoded'
      headers['Accept'] = 'application/vnd.siren+json'
      headers['Origin'] = 'https://www.peacocktv.com'
      headers['Referer'] = 'https://www.peacocktv.com/'
      #print_json(headers)

      h = {}
      headers.update(h)

      post_data = 'userIdentifier=' + username +'&password=' + password
      response = self.net.session.post(url, data=post_data, headers=headers)
      print(response.content)

      cookie_dict = requests.utils.dict_from_cookiejar(response.cookies)
      cookie_string = '; '.join([key + '=' + value for key, value in cookie_dict.iteritems()])
      #print(cookie_string)
      self.account['cookie'] = cookie_string

      data = json.loads(response.content)
      #print_json(data)
      if data.get('properties', []).get('eventType') == 'success':
        device_id = data['properties']['data']['deviceid']
        self.account['device_id'] = device_id
        self.account['cookie'] += '; deviceid=' + device_id
        cookie_filename = self.pldir + '/cookie.conf'
        self.cache.save_file(cookie_filename, self.account['cookie'])
        return True, response.content

      return False, response.content

    def get_profiles(self):
      url = self.endpoints['profiles']
      headers = self.net.headers.copy()
      headers['content-type'] = 'application/json'
      headers['cookie'] = self.account['cookie']
      data = self.net.post_data(url, '', headers)
      res = []
      if 'personas' in data:
        for d in data['personas']:
          p = {'id': d['id'], 'name': d['displayName'], 'type': d['type'], 
               'avatar': d['avatar']['links']['AvatarWithBackgroundTransparency']['href']}
          p['avatar'] = p['avatar'].replace('{width}/{height}', '400')
          res.append(p)
      return res

    def change_profile(self, id):
      self.account['profile_id'] = id
      self.cache.save_file(self.pldir + '/profile_id.conf', self.account['profile_id'])
      self.cache.remove_file(self.pldir + '/token.json')

    def get_my_stuff_slug(self):
      url = self.endpoints['my-stuff'].format(slug='/my-stuff')
      data = self.net.load_data(url)
      slug = data['data']['group']['slug']
      return slug

    def get_my_list(self):
      url = self.endpoints['my-list'].format(slug=self.get_my_stuff_slug())
      headers = self.net.headers.copy()
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      sig_header = calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      #print_json(data)
      #self.cache.save_json('my-list.json', data)
      if 'rails' in data:
        rails = list(data["rails"].items())
        return self.parse_catalog(rails[0][1]['items'])
      return None

    def get_localisation(self):
      url = self.endpoints['localisation']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.localisationinfo.v1+json'
      headers['cookie'] = self.account['cookie']
      sig_header = calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      return data

    def get_me(self):
      url = self.endpoints['me']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.userinfo.v2+json'
      headers['Content-Type'] = 'application/vnd.userinfo.v2+json'
      headers['x-skyott-usertoken'] = self.account['user_token']
      sig_header = calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      return data

    def create_device_id(self):
      import random
      import string
      s = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
      return s

    def get_tokens(self):
      url = self.endpoints['tokens']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.tokens.v1+json'
      headers['Content-Type'] = 'application/vnd.tokens.v1+json'
      headers['cookie'] = self.account['cookie']
      post_data = {
        "auth": {
            "authScheme": "MESSO",
            "authIssuer": "NOWTV",
            "provider": self.platform['headers']['x-skyott-provider'],
            "providerTerritory": self.platform['headers']['x-skyott-territory'],
            "proposition": self.platform['headers']['x-skyott-proposition'],
            "personaId": self.account['profile_id']
        },
        "device": {
           "type": "COMPUTER",
           "platform": "PC",
           "id": self.platform['device_id'],
           "drmDeviceId": "UNKNOWN"
        }
      }
      post_data = json.dumps(post_data)
      sig_header = calculate_signature('POST', url, headers, post_data)
      headers.update(sig_header)
      data = self.net.post_data(url, post_data, headers)
      return data

    def get_playback_info(self, content_id, provider_variant_id):
      url = self.endpoints['playouts']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.playvod.v1+json'
      headers['Content-Type'] = 'application/vnd.playvod.v1+json'
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      post_data = {
        "device": {
           "capabilities": [
             {
                "protection": "WIDEVINE",
                "container": "ISOBMFF",
                "transport": "DASH",
                "acodec": "AAC",
                "vcodec": "H264"
            },
            {
                "protection": "NONE",
                "container": "ISOBMFF",
                "transport": "DASH",
                "acodec": "AAC",
                "vcodec": "H264"
            }
          ],
          "maxVideoFormat": "HD",
          "model": "PC",
          "hdcpEnabled": "true",
        },
        "client": {
          "thirdParties": [
            "FREEWHEEL"
          ]
        },
        "contentId": content_id,
        "providerVariantId": provider_variant_id,
        "parentalControlPin": "null",
        "personaParentalControlRating": "9"
      }
      post_data = json.dumps(post_data)
      sig_header = calculate_signature('POST', url, headers, post_data)
      headers.update(sig_header)
      #print_json(headers)

      response = self.net.session.post(url, headers=headers, data=post_data)
      content = response.content.decode('utf-8')
      LOG(content)
      data = json.loads(content)
      #print_json(data)
      #self.cache.save_json('playback.json', data)

      res = {'response': data}
      if 'protection' in data:
        res.update(
              {'license_url': data['protection']['licenceAcquisitionUrl'],
               'license_token': data['protection']['licenceToken'],
               'manifest_url': data['asset']['endpoints'][0]['url']})
      return res

