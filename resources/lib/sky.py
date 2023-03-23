# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import sys
import json
import requests
import io
import os
import time
#import re
from datetime import datetime

from .log import LOG, print_json
from .network import Network
from .cache import Cache
from .endpoints import Endpoints
from .signature import calculate_signature
from .timeconv import timestamp2str

class SkyShowtime(object):

    platforms = {
      'skyshowtime': {
         'name': 'SkyShowtime',
         'host': 'skyshowtime.com',
         'config_dir': 'skyshowtime',
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

    account = {'username': None, 'password': None,
               'device_id': None,
               'profile_id': None, 'profile_type': None,
               'cookie': None, 'user_token': None}

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
        self.account['cookie'] = content.encode('utf-8').strip()
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
      content = self.cache.load_file(self.pldir + '/profile.json')
      if content:
        profile = json.loads(content)
        self.account['profile_id'] = profile['id']
        self.account['profile_type'] = profile['type']
      else:
        self.account['profile_id'], self.account['profile_type'] = self.select_default_profile()

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

      # Search
      data = self.cache.load_file('searchs.json')
      self.search_list = json.loads(data) if data else []

    def get_art(self, images):
      def image_url(url):
        return url.replace('?language', '/400?language')

      art = {'icon': None, 'poster': None, 'fanart': None, 'thumb': None}
      title34 = nontitle34 = None
      for i in images:
        if i['type'] == 'titleArt34':
          title34 = image_url(i['url'])
        elif i['type'] == 'nonTitleArt34':
          nontitle34 = image_url(i['url'])
        elif i['type'] == 'titleArt169':
          art['poster'] = image_url(i['url'])
        elif i['type'] == 'landscape':
          art['fanart'] = image_url(i['url'])
        elif i['type'] == 'titleLogo':
          art['clearlogo'] = image_url(i['url'])
        elif i['type'] == 'scene169':
          art['thumb'] = image_url(i['url'])
        if title34 and not art['poster']: art['poster'] = title34
        if nontitle34 and not art['poster']: art['poster'] = nontitle34
        if not art['thumb']: art['thumb'] = art['poster']
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
        t['slug'] = e.get('slug')
        t['info']['title'] = e['title']
        if e['type'] == 'CATALOGUE/COLLECTION':
          t['type'] = 'category'
          res.append(t)
        elif e['type'] == 'CATALOGUE/LINK':
          t['type'] = 'category'
          if 'linkInfo' in e:
            t['slug'] = e['linkInfo']['slug']
            t['id'] = e['linkInfo']['nodeId']
            res.append(t)
          else:
            LOG('link not supported: {} ({})'.format(t['slug'], e['linkId']))
        elif e['type'] in ['ASSET/PROGRAMME', 'ASSET/SLE', 'ASSET/SHORTFORM/CLIP', 'ASSET/EPISODE']:
          t['type'] = 'movie'
          t['info']['mediatype'] = 'movie'
          t['info']['year'] = e.get('year')
          t['info']['duration'] = e['duration']['durationSeconds']
          t['info']['mpaa'] = e.get('ottCertificate')
          t['info']['plot'] = e.get('synopsisLong')
          t['art'] = self.get_art(e['images'])
          t['info']['genre'] = self.get_genres(e['genreList'])
          if e['type'] == 'ASSET/EPISODE':
            t['info']['mediatype'] = 'episode'
            t['info']['tvshowtitle'] = e['seriesName']
            t['info']['season'] = e['seasonNumber']
            t['info']['episode'] = e['number']
          res.append(t)
        elif e['type'] == 'CATALOGUE/SERIES':
          t['type'] = 'series'
          t['info']['mediatype'] = 'tvshow'
          t['info']['mpaa'] = e.get('ottCertificate')
          t['info']['plot'] = e.get('synopsisLong')
          t['art'] = self.get_art(e['images'])
          t['info']['genre'] = self.get_genres(e['genreList'])
          res.append(t)
        else:
          LOG('catalog type not supported: {}'.format(e['type']))
        if 'displayStartTime' in e:
          t['info']['title'] = '[COLOR yellow]{}[/COLOR] - {}'.format(timestamp2str(e['displayStartTime']/1000, '%a %d %H:%M'), t['info']['title'])
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
      if e['type'] == 'CATALOGUE/SERIES':
        t['type'] = 'series'
        t['info']['mediatype'] = 'tvshow'
        t['info']['plot'] = att.get('synopsisLong')
      elif e['type'] == 'CATALOGUE/SEASON':
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
        t['type'] = 'movie'
        t['info']['mediatype'] = 'movie'
        t['info']['year'] = e.get('year')
      if e['type'] in ['ASSET/PROGRAMME', 'ASSET/EPISODE', 'ASSET/SLE', 'ASSET/SHORTFORM/CLIP']:
        t['info']['plot'] = att['synopsisLong']
        t['info']['duration'] = att['durationSeconds']
        t['info']['mpaa'] = att.get('ottCertificate')
        t['content_id'] = att.get('nbcuId')
        if 'formats' in att:
          if 'HD' in att['formats']:
            t['content_id'] = att['formats']['HD']['contentId']
          elif 'SD' in att['formats']:
            t['content_id'] = att['formats']['SD']['contentId']
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
      #self.cache.save_json('catalog.json', data)
      if 'rail' in data['data']:
        items = data['data']['rail']['items']
      else:
        items = data['data']['group']['rails']
      return self.parse_catalog(items)

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
      #self.cache.save_json('series.json', data)
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

    def delete_cookie(self):
      cookie_filename = self.pldir + '/cookie.conf'
      self.cache.remove_file(cookie_filename)

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

    def select_default_profile(self):
      profiles = self.get_profiles()
      if len(profiles) > 0:
        profile = profiles[0]
        self.cache.save_json(self.pldir + '/profile.json', profile)
        return profile['id'], profile['type']
      return None, None

    def change_profile(self, id):
      profiles = self.get_profiles()
      for profile in profiles:
        if profile['id'] == id:
          self.cache.save_json(self.pldir + '/profile.json', profile)
          self.cache.remove_file(self.pldir + '/token.json')
          return
      else:
        LOG('profile {} not found'.format(id))

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
      if 'rails' in data and len(data['rails']) > 0:
        rails = list(data["rails"].items())
        return self.parse_catalog(rails[0][1]['items'])
      return []

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
      if self.account['user_token']:
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

    def request_playback_tokens(self, url, post_data, content_type, preferred_server=''):
      headers = self.net.headers.copy()
      headers['Accept'] = content_type
      headers['Content-Type'] = content_type
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
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
        manifest_url = None
        for i in data['asset']['endpoints']:
          if not manifest_url:
            manifest_url = i['url']
          if i['cdn'].lower() == preferred_server.lower():
            manifest_url = i['url']
            break
        res.update(
              {'license_url': data['protection']['licenceAcquisitionUrl'],
               'license_token': data['protection']['licenceToken'],
               'manifest_url': manifest_url})
      return res

    def get_playback_info(self, content_id, provider_variant_id, preferred_server=''):
      url = self.endpoints['playouts']
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
      return self.request_playback_tokens(url, post_data, 'application/vnd.playvod.v1+json', preferred_server)

    def get_live_playback_info(self, service_key, preferred_server=''):
      url = self.endpoints['playouts-live']
      post_data = {
        "serviceKey": service_key,
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
          "hdcpEnabled": "true"
        },
        "client": {
          "thirdParties": ["FREEWHEEL"],
          "timeShiftEnabled": "false"
        },
        "parentalControlPin": "null",
        "personaParentalControlRating": "9"
      }
      return self.request_playback_tokens(url, post_data, 'application/vnd.playlive.v1+json', preferred_server)

    def add_search(self, search_term):
      self.search_list.append(search_term)
      self.cache.save_json('searchs.json', self.search_list)

    def delete_search(self, search_term):
      self.search_list = [s for s in self.search_list if s != search_term]
      self.cache.save_json('searchs.json', self.search_list)

    def search_vod(self, search_term):
      res = []
      url = self.endpoints['search-vod'].format(search_term=search_term)
      data = self.net.load_data(url)
      #print_json(data)
      if not 'results' in data: return None
      res = []
      for i in data['results']:
        if 'uuid' in i:
          url = self.endpoints['get-video-info-uuid'].format(uuid=i['uuid'])
          #if i['uuidtype'] == 'series': LOG(url)
          d = self.net.load_data(url)
          t = self.parse_item(d[0])
          res.append(t)
      return res

    def get_main_menu(self):
      def find_item(term, items):
        for i in items:
          #print(i['attributes']['alias'])
          if i['attributes']['alias'] == term:
            return i
        return None

      cache_filename = self.pldir +'/menu.json'
      content = self.cache.load(cache_filename)
      if content:
        data = json.loads(content)
      else:
        url = self.endpoints['menu']
        data = self.net.load_data(url)
        self.cache.save_json(cache_filename, data)

      res = []
      if self.account['profile_type'] == 'Kid':
        top_label = 'kidsTopNavWithIcons'
        main_label = 'Kids'
      else:
        top_label = 'topNavWithIcons'
        main_label = 'Main'
      topnav = find_item(top_label, data['relationships']['items']['data'])
      #print_json(topnav)
      #self.cache.save_json('topnav.json', topnav)
      if topnav:
        main = find_item(main_label, topnav['relationships']['items']['data'])
        if main:
          for i in main['relationships']['items']['data']:
            #print(i['attributes']['alias'])
            att = i['attributes']
            try:
              rel = i['relationships']
              icon = rel['images']['data'][0]['attributes']['url']
            except:
              icon = None
            t = {'id': att['alias'], 'title': att['title'], 'slug': att['uri'].replace('/watch',''), 'icon': icon}
            res.append(t)
      return res

    def download_epg(self):
      cache_filename = 'cache/epg.json'
      content = self.cache.load(cache_filename, 60)
      if content:
        data = json.loads(content)
        return data

      if sys.version_info[0] >= 3:
        from urllib.parse import quote
      else:
        from urllib import quote
      from dateutil import tz
      now = datetime.now(tz.tzlocal())
      now = now.replace(minute=0, second=0, microsecond=0)
      date = now.strftime('%Y-%m-%dT%H:%M%z')
      date = date[:-2] + ':' + date[-2:]
      url = self.endpoints['epg'].format(start_time=quote(date))
      #print(url)
      data = self.net.load_data(url)
      self.cache.save_json(cache_filename, data)
      return data

    def get_channels(self):
      epg = self.download_epg()
      res = []
      for c in epg['channels']:
        t = {'info': {}}
        t['art'] = {'icon': None, 'poster': None, 'fanart': None, 'thumb': None}
        t['type'] = 'movie'
        t['stream_type'] = 'tv'
        t['info']['mediatype'] = 'movie'
        t['dial'] = str(c['rank'])
        t['info']['title'] = t['dial'] +'. ' + c['name']
        t['channel_name'] = c['name']
        t['id'] = c['id']
        t['service_key'] = c['serviceKey']
        t['info']['playcount'] = 1 # Set as watched
        if 'images' in c:
          t['art'] = self.get_art(c['images'])
        t['channel_type'] = c['type']
        res.append(t)
      return res

    def get_channels_with_epg(self):
      now = time.time()
      channels = self.get_channels()
      epg = self.get_epg()
      for ch in channels:
        p = self.find_program_epg(epg, ch['service_key'], now)
        #print_json(p)
        if p:
          ch['info']['plot'] = p['info']['plot']
          ch['info']['title'] += ' - [COLOR yellow]' + p['info']['title'] + '[/COLOR]'
          ch['info']['duration'] = p['info']['duration']
          if p['art']['poster']: ch['art']['poster'] = p['art']['poster']
          if p['content_id'] and p['provider_variant_id']:
            ch['content_id'] = p['content_id']
            ch['provider_variant_id'] = p['provider_variant_id']
      return channels

    def get_epg(self):
      def find_image(data):
        url = None
        for label in ['16-9', 'scene169', 'landscape']:
          url = data.get(label)
          if url: break
        if url:
          url = url.replace('?', '/400?')
        return url

      epg = self.download_epg()
      res = {}
      for c in epg['channels']:
        id = c['serviceKey']
        res[id] = []
        for i in c['scheduleItems']:
          #print_json(i)
          t = {'info': {}, 'art': {'poster': None}}
          t['start'] = i['startTimeUTC']
          t['end'] = t['start'] + i['durationSeconds']
          t['start_str'] = timestamp2str(t['start'])
          t['end_str'] = timestamp2str(t['end'])
          t['date_str'] = timestamp2str(t['start'], '%a %d %H:%M')
          t['info']['title'] = i['data']['title']
          t['info']['plot'] = i['data'].get('description')
          t['info']['duration'] = i['durationSeconds']
          if 'images' in i['data']:
            t['art']['poster'] = find_image(i['data']['images'])
          t['content_id'] = i['data'].get('contentId')
          t['provider_variant_id'] = i['data'].get('providerVariantId')
          res[id].append(t)
      return res

    def find_program_epg(self, epg, service_key, timestamp = None):
      id = service_key
      if not timestamp: timestamp = time.time()
      for p in epg[id]:
        #print(p)
        if (p['start'] <= timestamp) and (timestamp <= p['end']):
          return p
      return None

    def import_key_file(self, filename):
      if sys.version_info[0] > 2:
        filename = bytes(filename, 'utf-8')
      with io.open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
        output_dir = 'peacocktv' if 'peacocktv' in data['host'] else 'skyshowtime'
        self.cache.save_file(output_dir + '/cookie.conf', data['data'])

    def export_key_file(self, filename):
      if sys.version_info[0] > 2:
        filename = bytes(filename, 'utf-8')
      data = {'app_name': 'skyott', 'timestamp': str(int(time.time()*1000)),
              'host': 'https://www.' + self.platform['host'],
              'data': self.account['cookie'].decode('utf-8')}
      #print_json(data)
      with io.open(filename, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False))

    def install_cookie_file(self, filename):
      import shutil
      if sys.version_info[0] > 2:
        filename = bytes(filename, 'utf-8')
      shutil.copyfile(filename, self.cache.config_directory + self.pldir + '/cookie.conf')
