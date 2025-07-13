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
import re
from datetime import datetime

from .log import LOG, print_json
from .network import Network
from .cache import Cache
from .endpoints import Endpoints
from .signature import Signature
from .timeconv import timestamp2str
from .user_agent import user_agent, chrome_user_agent

class SkyShowtime(object):

    platforms = {
      'skyshowtime': {
         'name': 'SkyShowtime',
         'host': 'skyshowtime.com',
         'config_dir': 'skyshowtime',
         'appnamespace': None,
         'use_nowtv_api': False,
         'headers': {
           'x-skyott-activeterritory': 'ES',
           'x-skyott-client-version': '4.3.12',
           'x-skyott-device': 'MOBILE',
           'x-skyott-language': 'en-US',
           'x-skyott-platform': 'ANDROID',
           'x-skyott-proposition': 'SKYSHOWTIME',
           'x-skyott-provider': 'SKYSHOWTIME',
           'x-skyott-territory': 'ES'
         },
      },
      'peacocktv': {
         'name': 'PeacockTV',
         'host': 'peacocktv.com',
         'config_dir': 'peacocktv',
         'appnamespace': None,
         'use_nowtv_api': False,
         'headers': {
           'x-skyott-activeterritory': 'US',
           'x-skyott-client-version': '4.3.12',
           'x-skyott-device': 'MOBILE',
           'x-skyott-language': 'en',
           'x-skyott-platform': 'ANDROID',
           'x-skyott-proposition': 'NBCUOTT',
           'x-skyott-provider': 'NBCU',
           'x-skyott-territory': 'US'
         }
      },
      'nowtv': {
         'name': 'NowTV',
         'host': 'nowtv.com',
         'config_dir': 'nowtv',
         'appnamespace': 'NOWUK',
         'use_nowtv_api': True,
         'headers': {
           'x-skyott-activeterritory': 'GB',
           'x-skyott-client-version': '4.3.12',
           'x-skyott-device': 'MOBILE',
           'x-skyott-language': 'en-US',
           'x-skyott-platform': 'ANDROID',
           'x-skyott-proposition': 'NOWOTT',
           'x-skyott-provider': 'NOWTV',
           'x-skyott-territory': 'GB'
         }
      },
      'wowtv': {
         'name': 'WowTV',
         'host': 'wowtv.de',
         'config_dir': 'wowtv',
         'appnamespace': 'NOWDEUTSCHLAND',
         'use_nowtv_api': True,
         'headers': {
           'x-skyott-activeterritory': 'DE',
           'x-skyott-client-version': '4.3.12',
           'x-skyott-device': 'TV',
           'x-skyott-language': 'de-DE',
           'x-skyott-platform': 'ANDROIDTV',
           'x-skyott-proposition': 'NOWOTT',
           'x-skyott-provider': 'NOWTV',
           'x-skyott-territory': 'DE'
         },
      },
      'nowtv-it': {
         'name': 'NowTV-IT',
         'host': 'nowtv.it',
         'config_dir': 'nowtv-it',
         'appnamespace': 'NOWITALIA',
         'use_nowtv_api': True,
         'headers': {
           'x-skyott-activeterritory': 'IT',
           'x-skyott-client-version': '4.3.12',
           'x-skyott-device': 'TV',
           'x-skyott-language': 'it-IT',
           'x-skyott-platform': 'ANDROIDTV',
           'x-skyott-proposition': 'NOWOTT',
           'x-skyott-provider': 'NOWTV',
           'x-skyott-territory': 'IT'
         },
      }
    }

    account = {'username': None, 'password': None,
               'device_id': None,
               'profile_id': None, 'profile_type': None,
               'my_segments': [], 'my_discovery': [],
               'account_type': [],
               'cookie': None, 'user_token': None}
    get_token_error = ''

    def __init__(self, config_directory, platform='skyshowtime', territory=None):
      self.logged = False

      self.platform = self.platforms[platform]
      self.pldir = self.platform['config_dir']
      if not os.path.exists(config_directory + self.pldir):
        os.makedirs(config_directory + self.pldir)

      # Signature
      self.sig = Signature(platform)

      # Network
      default_headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'User-Agent': user_agent(platform),
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

      # Get the territory from the cookie
      if not territory and self.account['cookie']:
        m = re.search(b'(?:hterr|userTerritory|activeTerritory)=([A-Z]{2})', self.account['cookie'])
        if m: territory = m.group(1).decode('utf-8')
      LOG('territory: {}'.format(territory))

      # Load localisation
      localisation_filename = self.pldir + '/localisation.json'
      content = self.cache.load(localisation_filename)
      if content:
        extra_headers = json.loads(content)
      else:
        extra_headers = self.get_localisation()
        if 'headers' in extra_headers:
          self.cache.save_json(localisation_filename, extra_headers)
      if extra_headers and 'headers' in extra_headers:
        h = extra_headers['headers']
        self.platform['headers'].update({
             'x-skyott-activeterritory': h.get('x-skyott-activeterritory'),
             'x-skyott-language': h.get('x-skyott-language'),
             'x-skyott-territory': h.get('x-skyott-territory'),
        })
        for key in ['x-skyott-bouquetId', 'x-skyott-subBouquetId', 'x-skyott-broadcastRegions']:
          if key in h:
            self.platform['headers'][key] = h[key]

      # Override data from localisation if the user set a territory
      if territory:
        self.platform['headers']['x-skyott-territory'] = territory
        if self.platform['headers']['x-skyott-activeterritory'] == 'XX':
          self.platform['headers']['x-skyott-activeterritory'] = territory
      self.net.headers.update(self.platform['headers'])
      #print_json(self.platform['headers'])
      #print_json(self.net.headers)

      # From this point the cookie is needed
      if not self.logged: return

      # Load profile
      content = self.cache.load_file(self.pldir + '/profile.json')
      if content:
        profile = json.loads(content)
        self.account['profile_id'] = profile['id']
        self.account['profile_type'] = profile['type']
      else:
        self.account['profile_id'], self.account['profile_type'] = self.select_default_profile()

      if self.account['profile_id']:
         profile_info_filename = self.pldir + '/profile_info.json'
         content = self.cache.load_file(profile_info_filename)
         if content:
           data = json.loads(content)
         else:
           data = self.get_profile_info(self.account['profile_id'])
           self.cache.save_json(profile_info_filename, data)
         if 'persona' in data and 'displayLanguage' in data['persona']:
           self.platform['headers']['x-skyott-language'] = data['persona']['displayLanguage']
           self.net.headers.update(self.platform['headers'])
         if 'persona' in data:
           #print_json(data['persona'])
           self.account['freewheel'] = data['persona']['obfuscatedIds']['freewheel']

      # Load user token
      token_filename = self.pldir + '/token.json'
      content = self.cache.load(token_filename, 60)
      if content:
        data = json.loads(content)
      else:
        data = self.get_tokens()
        if 'userToken' in data:
          self.cache.save_json(token_filename, data)
        if 'description' in data:
          self.get_token_error = data['description']
      if data and 'userToken' in data:
        self.account['user_token'] = data['userToken']

      # Search
      data = self.cache.load_file('searchs.json')
      self.search_list = json.loads(data) if data else []

      # Load my segments
      if self.account['user_token']:
        me_filename = self.pldir + '/me.json'
        content = self.cache.load(me_filename)
        if content:
          data = json.loads(content)
        else:
          data = self.get_me()
          self.cache.save_json(me_filename, data)
        for s in data.get('segmentation', []).get('content', []):
          self.account['my_segments'].append(s['name'])
        for s in data.get('segmentation', []).get('discovery', []):
          self.account['my_discovery'].append(s['name'])
        for s in data.get('segmentation', []).get('account', []):
          self.account['account_type'].append(s['name'])
        self.account['content'] = ','.join(self.account['my_segments'])
        self.account['discovery'] = ','.join(self.account['my_discovery'])

    def is_subscribed(self, segments):
      if not segments: return True
      for s in self.account['my_segments']:
        if s in segments: return True
      return False

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
        if 'displayStartTime' in e:
          t['info']['title'] = '[COLOR yellow]{}[/COLOR] - {}'.format(timestamp2str(e['displayStartTime']/1000, '%a %d %H:%M'), t['info']['title'])
        if 'contentSegments' in e:
          t['segments'] = e['contentSegments']
          t['subscribed'] = self.is_subscribed(t['segments'])
        if 'formats' in e:
          if 'HD' in e['formats']:
            t['offer'] = {'start': e['formats']['HD'].get('availability', []).get('offerStartTs', 0),
                          'end': e['formats']['HD'].get('availability', []).get('offerEndTs', 0) }
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
          if 'duration' in e:
            t['info']['duration'] = e['duration']['durationSeconds']
          elif 'durationSeconds' in e:
            t['info']['duration'] = e['durationSeconds']
          t['info']['mpaa'] = e.get('ottCertificate')
          t['info']['plot'] = e.get('synopsisLong')
          t['art'] = self.get_art(e['images'])
          t['info']['genre'] = self.get_genres(e['genreList'])
          if e['type'] == 'ASSET/EPISODE':
            t['info']['mediatype'] = 'episode'
            t['info']['tvshowtitle'] = e['seriesName']
            t['info']['season'] = e['seasonNumber']
            t['info']['episode'] = e['number']
          if 'streamPosition' in e:
            t['stream_position'] = e['streamPosition']
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
      t['bookmark_metadata'] = {}
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
        #t['content_id'] = att.get('nbcuId')
        if 'formats' in att:
          if 'HD' in att['formats']:
            t['content_id'] = att['formats']['HD']['contentId']
            if 'startOfCredits' in att['formats']['HD']:
              t['bookmark_metadata']['startOfCredits'] = att['formats']['HD']['startOfCredits']
            if 'markers' in att['formats']['HD']:
              t['markers'] = att['formats']['HD']['markers']
          elif 'SD' in att['formats']:
            t['content_id'] = att['formats']['SD']['contentId']
        t['provider_variant_id'] = att.get('providerVariantId')
      if 'formats' in att:
        if 'HD' in att['formats']:
            t['offer'] = {'start': att['formats']['HD'].get('availability', []).get('offerStartTs', 0),
                          'end': att['formats']['HD'].get('availability', []).get('offerEndTs', 0) }
      if 'programmeUuid' in att:
        t['uuid'] = att['programmeUuid']
      elif 'seriesUuid' in att:
        t['uuid'] = att['seriesUuid']
      if 'providerSeriesId' in att:
        t['bookmark_metadata']['providerSeriesId'] = att['providerSeriesId']
      if 'contentSegments' in att:
        t['segments'] = att['contentSegments']
        t['subscribed'] = self.is_subscribed(t['segments'])
      return t

    def parse_items(self, data):
      res = []
      for e in data:
        t = self.parse_item(e)
        res.append(t)
      return res

    def get_catalog(self, slug):
      url = self.endpoints['section'].format(slug=slug)
      #LOG(url)
      data = self.net.load_data(url)
      #LOG(data)
      #SkyShowtime.save_file('/tmp/catalog.json', data)
      if 'rail' in data['data']:
        items = data['data']['rail'].get('items', [])
        if self.platform['use_nowtv_api']:
            rail_id = data['data']['rail']['id']
            items = self.get_rails(rail_id)
      elif 'group' in data['data']:
        items = data['data']['group'].get('rails', [])
        if self.platform['use_nowtv_api']:
          group_id = data['data']['group']['id']
          items = self.get_browse_page(group_id)
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
      if self.platform['use_nowtv_api']:
        url += '&contentSegments={}'.format(self.account['content'])
      #LOG(url)
      data = self.net.load_data(url)
      #print_json(data)
      #SkyShowtime.save_file('/tmp/series.json', data)
      if 'relationships' in data:
        return self.parse_items(data['relationships']['items']['data'])
      else:
        return []

    def get_seasons(self, slug):
      return self.get_series_info(slug)

    def get_episodes(self, slug):
      return self.get_series_info(slug)

    def get_video_info(self, slug):
      url = self.endpoints['get-video-info'].format(slug=slug)
      if self.platform['use_nowtv_api']:
        url += '&contentSegments={}'.format(self.account['content'])
      #LOG(url)
      data = self.net.load_data(url)
      #print_json(data)
      #SkyShowtime.save_file('/tmp/movies.json', data)
      return self.parse_item(data)

    def get_video_info_uuid(self, uuid):
      url = self.endpoints['get-video-info-uuid'].format(uuid=uuid)
      data = self.net.load_data(url)
      #SkyShowtime.save_file('/tmp/uuid_data.json', data)
      if len(data) > 0:
        return self.parse_item(data[0])
      else:
        return None

    def login(self, username='', password=''):
      url = self.endpoints['login']
      #print(url)
      headers = self.net.headers.copy()
      headers['content-type'] = 'application/x-www-form-urlencoded'
      headers['Accept'] = 'application/vnd.siren+json'
      #headers['User-Agent'] = chrome_user_agent
      del headers['x-skyott-device']
      del headers['x-skyott-platform']
      print_json(headers)

      post_data = {'userIdentifier': username, 'password': password, 'rememberMe': True, 'isWeb': True}
      #print(json.dumps(post_data))
      response = self.net.session.post(url, data=post_data, headers=headers)
      LOG('login response: {} retcode: {}'.format(response.content, response.status_code))
      LOG('login response headers:')
      print_json(dict(response.headers))

      cookie_dict = requests.utils.dict_from_cookiejar(response.cookies)
      LOG('login response cookies:')
      print_json(cookie_dict)
      cookie_string = '; '.join([key + '=' + value for key, value in cookie_dict.items()])
      #LOG('cookie: {}'.format(cookie_string))
      content = response.content.decode('utf-8')

      try:
        data = json.loads(content)
        #print_json(data)
        if data.get('properties', []).get('eventType') == 'success':
          #if not 'device' in cookie_string:
          #  device_id = data['properties']['data']['deviceid']
          #  cookie_string += '; deviceid=' + device_id
          #if not 'hterr' in cookie_string:
          #  cookie_string += '; hterr=' + response.headers.get('x-geo-origin', '')
          LOG('cookie: {}'.format(cookie_string))
          self.account['cookie'] = cookie_string
          cookie_filename = self.pldir + '/cookie.conf'
          self.cache.save_file(cookie_filename, self.account['cookie'])
          return True, content
      except:
        pass
      return False, content

    def delete_cookie(self):
      cookie_filename = self.pldir + '/cookie.conf'
      self.cache.remove_file(cookie_filename)

    def get_profiles(self):
      url = self.endpoints['profiles']
      headers = self.net.headers.copy()
      headers['content-type'] = 'application/json'
      headers['cookie'] = self.account['cookie']
      data = self.net.post_data(url, '', headers)
      #LOG('data: {}'.format(data))
      res = []
      if 'personas' in data:
        for d in data['personas']:
          p = {'id': d['id'], 'name': d['displayName'], 'type': d['type'], 
               'avatar': ''}
          if 'avatar' in d:
            p['avatar'] = d['avatar']['links']['AvatarWithBackgroundTransparency']['href']
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
          files = ['profile_info.json', 'token.json', 'menu.json']
          for f in files:
            self.cache.remove_file(self.pldir +'/'+ f)
          return
      else:
        LOG('profile {} not found'.format(id))

    def get_my_stuff_slug(self):
      url = self.endpoints['my-stuff'].format(slug='/my-stuff')
      #LOG(url)
      data = self.net.load_data(url)
      #LOG(data)
      slug = data['data']['group']['slug']
      return slug

    def get_my_list(self):
      if self.platform['use_nowtv_api']:
        return self.get_my_section2('/home/watchlist', 'WATCHLIST')
      else:
        return self.get_my_section(self.get_my_stuff_slug())

    def get_continue_watching(self):
      if self.platform['use_nowtv_api']:
        return self.get_my_section2('/home/continue-watching', 'CONTINUE_WATCHING')
      else:
        return self.get_my_section('/home/continue-watching')

    def get_my_section(self, slug):
      url = self.endpoints['my-section'].format(slug=slug)
      #LOG(url)
      headers = self.net.headers.copy()
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      #print_json(data)
      #SkyShowtime.save_file('/tmp/my-section.json', data)
      if 'rails' in data and len(data['rails']) > 0:
        rails = list(data["rails"].items())
        return self.parse_catalog(rails[0][1]['items'])
      return []

    def get_my_section2(self, slug, rtype):
      url = self.endpoints['my-stuff'].format(slug=slug)
      #LOG(url)
      data = self.net.load_data(url)
      #LOG(data)
      id = data['data']['rail']['id']
      #LOG('rail id:{}'.format(id))
      res = self.get_rails(id, rtype=rtype)
      return self.parse_catalog(res)

    def get_rails(self, id, rtype=None):
      url = self.endpoints['get-rails'].format(id=id)
      if self.platform['use_nowtv_api']:
        url += '&discovery_content_segments={0}&playout_content_segments={0}'.format(self.account['discovery'])
      if rtype:
          url += '&type=' + rtype
      #LOG(url)
      headers = self.net.headers.copy()
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      #print_json(headers)
      data = self.net.load_data(url, headers)
      #print_json(data)
      #SkyShowtime.save_file('/tmp/rails.json', data)
      #print(data)
      res = []
      try:
        for tile in data['data']['tiles']:
          res.append(tile['tileInfo'])
      except (KeyError, TypeError):
        pass
      #print_json(res)
      return res

    def get_browse_page(self, id):
      url = self.endpoints['browse-page'].format(id=id)
      if self.platform['use_nowtv_api']:
        url += '&discovery_content_segments={}'.format(self.account['discovery'])
      #LOG(url)
      headers = self.net.headers.copy()
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      #print_json(headers)
      data = self.net.load_data(url, headers)
      #SkyShowtime.save_file('/tmp/browse.json', data)
      #LOG(data)
      res = []
      try:
        for rail in data['data']['rails']:
          res.append(rail['railInfo'])
        for tile in data['data']['tiles']:
          res.append(tile['tileInfo'])
      except (KeyError, TypeError):
        pass
      return res

    def get_localisation(self):
      url = self.endpoints['localisation']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.localisationinfo.v1+json'
      #headers['cookie'] = self.account['cookie']
      headers['x-skyott-provider'] = self.platform['headers']['x-skyott-provider']
      headers['x-skyott-proposition'] = self.platform['headers']['x-skyott-proposition']
      if self.platform['appnamespace']:
        headers['x-skyott-appnamespace'] = self.platform['appnamespace']
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      #print_json(headers)
      LOG(headers)
      data = self.net.load_data(url, headers)
      LOG('get_localisation: data: {}'.format(data))
      return data

    def get_me(self):
      url = self.endpoints['me']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.userinfo.v2+json'
      headers['Content-Type'] = 'application/vnd.userinfo.v2+json'
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      #SkyShowtime.save_file('/tmp/me.json', data)
      return data

    def get_profile_info(self, profile_id):
      url = self.endpoints['get-profile-info'].format(profile_id=profile_id)
      headers = self.net.headers.copy()
      headers['Content-Type'] = 'application/json'
      headers['cookie'] = self.account['cookie']
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      return data

    def create_device_id(self):
      import random
      import string
      s = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
      return s

    def get_tokens(self, access_token=None):
      url = self.endpoints['tokens']
      #headers = self.net.headers.copy()
      headers = {}
      headers['Accept'] = 'application/vnd.tokens.v1+json'
      headers['Content-Type'] = 'application/vnd.tokens.v1+json'
      if not access_token:
        headers['cookie'] = self.account['cookie']
        auth = {
          "authScheme": "MESSO",
          "authIssuer": "NOWTV",
          "personaId": self.account['profile_id']
        }
      else:
        auth = {
          "authScheme": "OAUTH",
          "authToken": access_token
        }
      auth.update({
        "provider": self.platform['headers']['x-skyott-provider'],
        "providerTerritory": self.platform['headers']['x-skyott-territory'],
        "proposition": self.platform['headers']['x-skyott-proposition']
      })
      post_data = {
        "auth": auth,
        "device": {
           "type": "MOBILE",
           "platform": "ANDROID",
           "id": self.platform['device_id'],
           "drmDeviceId": "UNKNOWN"
        }
      }
      if self.platform['name'] in ['WowTV', 'NowTV-IT']:
         post_data['device']['type'] = 'TV'
         post_data['device']['platform'] = 'ANDROIDTV'
      LOG('get_tokens: post_data: {}'.format(post_data))
      post_data = json.dumps(post_data)
      sig_header = self.sig.calculate_signature('POST', url, headers, post_data)
      headers.update(sig_header)
      data = self.net.post_data(url, post_data, headers)
      headers['cookie'] = '<redacted>'
      LOG('get_tokens: headers: {}'.format(headers))
      LOG('get_tokens: response data: {}'.format(data))
      return data

    def request_playback_tokens(self, url, post_data, content_type, preferred_server=''):
      headers = self.net.headers.copy()
      headers['Accept'] = content_type
      headers['Content-Type'] = content_type
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      post_data = json.dumps(post_data)
      sig_header = self.sig.calculate_signature('POST', url, headers, post_data)
      headers.update(sig_header)
      #LOG(post_data)
      #print_json(headers)

      response = self.net.session.post(url, headers=headers, data=post_data)
      content = response.content.decode('utf-8')
      #LOG(content)
      data = json.loads(content)
      #print_json(data)
      #SkyShowtime.save_file('/tmp/playback.json', data)

      res = {'response': data}
      if 'asset' in data:
        manifest_url = None
        cdn = ''
        for i in data['asset']['endpoints']:
          if not manifest_url:
            manifest_url = i['url']
            cdn = i['cdn']
          if i['cdn'].lower() == preferred_server.lower():
            manifest_url = i['url']
            cdn = i['cdn']
            break
        if manifest_url:
          manifest_url += '&audio=all&subtitle=all&forcedNarrative=true&trickplay=true'
          #manifest_url += '&audioCodec=mp4a.40.2,mp4a.40.5'
        res['manifest_url'] = manifest_url
      if 'protection' in data:
        res['license_url'] = data['protection']['licenceAcquisitionUrl']
        res['license_token'] = data['protection']['licenceToken']
        res['cdn'] = cdn
      return res

    def create_playback_request(self, uhd, hdcpEnabled, hdr10, dolbyvision):
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
          "model": "Pixel",
          "hdcpEnabled": hdcpEnabled,
          "supportedColourSpaces": ["SDR"],
        },
        "client": {
          "thirdParties": [
            "FREEWHEEL"
          ]
        },
        "parentalControlPin": "null",
        "personaParentalControlRating": "19"
      }

      if uhd:
        post_data['device']['capabilities'].append(
          {"protection": "WIDEVINE", "container": "ISOBMFF", "transport": "DASH","acodec": "AAC", "vcodec": "H265"}
        )
        post_data['device']['maxVideoFormat'] = 'UHD'

        # Order is important
        post_data['device']['supportedColourSpaces'] = []
        if dolbyvision:
          post_data['device']['supportedColourSpaces'].append('DolbyVision')
        if hdr10:
          post_data['device']['supportedColourSpaces'].append('HDR10')
        post_data['device']['supportedColourSpaces'].append('SDR')

      return post_data

    def get_playback_info(self, content_id, provider_variant_id, preferred_server='', uhd=False, hdcpEnabled=False, hdr10=False, dolbyvision=False):
      url = self.endpoints['playouts']
      post_data = self.create_playback_request(uhd=uhd, hdcpEnabled=hdcpEnabled, hdr10=hdr10, dolbyvision=dolbyvision)
      post_data.update({"contentId": content_id, "providerVariantId": provider_variant_id})
      print_json(post_data)
      return self.request_playback_tokens(url, post_data, 'application/vnd.playvod.v1+json', preferred_server)

    def get_live_playback_info(self, service_key, preferred_server='', uhd=False, hdcpEnabled=False, hdr10=False, dolbyvision=False):
      url = self.endpoints['playouts-live']
      post_data = self.create_playback_request(uhd=uhd, hdcpEnabled=hdcpEnabled, hdr10=hdr10, dolbyvision=dolbyvision)
      post_data["serviceKey"] = service_key
      post_data["client"]["timeShiftEnabled"] = "false"
      print_json(post_data)
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
      #SkyShowtime.save_file('/tmp/search_result.json', data)
      if not 'results' in data: return None
      res = []
      for i in data['results']:
        if 'uuid' in i:
          t = self.get_video_info_uuid(i['uuid'])
          if t:
            res.append(t)
      return res

    def search(self, search_term):
      url = self.endpoints['search'].format(search_term=search_term)
      if self.platform['use_nowtv_api']:
        url += '&contentSegment={}&discovery_content_segments={}'.format(self.account['content'], self.account['discovery'])
      #LOG(url)
      data = self.net.load_data(url)
      #print_json(data)
      #SkyShowtime.save_file('/tmp/search_result.json', data)
      return self.parse_catalog(data['data']['search']['results'])

    def download_menu(self):
      # MOBILE loads a different menu
      headers = self.net.headers.copy()
      headers['x-skyott-device'] = 'COMPUTER'
      headers['x-skyott-platform'] = 'PC'
      headers['User-Agent'] = chrome_user_agent
      #print_json(headers)
      url = self.endpoints['menu']
      #LOG(url)
      data = self.net.load_data(url, headers=headers)
      #SkyShowtime.save_file('/tmp/menu.json', data)
      return data

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
        data = self.download_menu()
        self.cache.save_json(cache_filename, data)

      res = []
      if self.account['profile_type'] == 'Kid':
        top_label = 'kidsTopNavWithIcons'
        main_label = 'Kids'
      else:
        top_label = 'topNavWithIcons'
        main_label = 'Main'

      if not 'relationships' in data: return res

      topnav = find_item(top_label, data['relationships']['items']['data'])
      #print_json(topnav)
      #SkyShowtime.save_file('/tmp/topnav.json', data)
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

            if 'uri' in att:
              slug = att['uri'].replace('/watch','')
            else:
              slug = i['relationships']['items']['data'][0]['attributes']['slug']
            #try:
            #  item_type = i['relationships']['items']['data'][0]['type']
            #  item_id = i['relationships']['items']['data'][0]['id']
            #except:
            #  item_type = None
            #  item_id = None
            t = {'id': att['alias'], 'title': att['title'], 'slug': slug, 'icon': icon}
            #t['type'] = item_type
            #t['item_id'] = item_id

            res.append(t)
      return res

    def to_watchlist(self, uuid=None, slug=None, action='add'):
      if slug:
         #uuid = slug.split('/')[-1]
         data = self.get_video_info(slug)
         uuid = data.get('uuid')
      url = self.endpoints['to-watchlist'].format(uuid=uuid)
      #LOG(url)
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.mytv.v3+json'
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      method = 'PUT' if action == 'add' else 'DELETE'
      sig_header = self.sig.calculate_signature(method, url, headers)
      headers.update(sig_header)
      #print_json(headers)
      if method == 'PUT':
        response = self.net.session.put(url, headers=headers)
      else:
        response = self.net.session.delete(url, headers=headers)
      content = response.content.decode('utf-8')
      LOG('to_mylist: result: {} {}'.format(response.status_code, content))
      if response.status_code != 201:
        data = json.loads(content)
        if 'errorCode' in data:
          return data['errorCode'], data['description']
      return response.status_code, ''

    def get_bookmarks(self):
      url = self.endpoints['get-bookmarks']
      #LOG(url)
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.bookmarking.v1+json'
      headers['Content-Type'] = 'application/vnd.bookmarking.v1+json'
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      return data

    def get_bookmark(self, content_id):
      url = self.endpoints['set-bookmark2'].format(content_id=content_id)
      #LOG(url)
      headers = self.net.headers.copy()
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      headers['Accept'] = 'application/vnd.bookmarks.v1+json'
      headers['Content-Type'] = 'application/vnd.bookmarks.v1+json'
      sig_header = self.sig.calculate_signature('GET', url, headers)
      headers.update(sig_header)
      data = self.net.load_data(url, headers)
      return data

    def set_bookmark(self, content_id, position):
      url = self.endpoints['set-bookmark2'].format(content_id=content_id)
      #LOG(url)
      headers = self.net.headers.copy()
      if self.account['user_token']:
        headers['x-skyott-usertoken'] = self.account['user_token']
      headers['Accept'] = 'application/vnd.bookmarks.v1+json'
      headers['Content-Type'] = 'application/vnd.bookmarks.v1+json'
      data = {"streamPositionSeconds": position}
      post_data = json.dumps(data)
      sig_header = self.sig.calculate_signature('PUT', url, headers, post_data)
      headers.update(sig_header)
      #print_json(headers)
      #LOG(post_data)
      try:
        response = self.net.session.put(url, headers=headers, data=post_data)
        content = response.content.decode('utf-8')
        LOG('set_bookmark: result: {} {}'.format(response.status_code, content))
        return response.status_code
      except:
        return 0

    def get_devices(self):
      url = self.endpoints['get-devices']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.bridge.v1+json'
      headers['cookie'] = self.account['cookie']
      data = self.net.load_data(url, headers)
      #LOG(data)
      res = []
      if 'devices' in data:
        for d in data['devices']:
          dev = {}
          dev['id'] = d['deviceid']
          dev['description'] = d['devicedescription']
          dev['signin_time'] = d.get('signintime', 0)
          dev['str_date'] = timestamp2str(dev['signin_time']/1000, '%d/%m/%Y %H:%M:%S')
          dev['alias'] = d['alias'] if d['alias'] else ''
          dev['type'] = d['type']
          if 'location' in d:
            dev['location'] = d['location']
          res.append(dev)
      return res

    def get_public_profile(self):
      url = self.endpoints['get-public-profile']
      headers = self.net.headers.copy()
      headers['Accept'] = 'application/vnd.aggregator.v3+json'
      headers['cookie'] = self.account['cookie']
      headers['Content-Type'] = 'application/vnd.aggregator.v3+json'
      data = self.net.load_data(url, headers)
      return data

    def download_epg(self):
      if self.account['profile_type'] == 'Kid':
        cache_filename = self.pldir + '/epg_kids.json'
      else:
        cache_filename = self.pldir + '/epg.json'
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
      if True:
        #url += '&playout_content_segments={0}&discovery_content_segments={0}'.format(self.account['discovery'])
        url += '&playout_content_segments={0}&discovery_content_segments={0}'.format(self.account['content'])
        #url += '&playout_content_segments={}'.format(self.account['content'])
        #url += '&playout_content_segments={}'.format(self.account['discovery'])
        if self.account['profile_type'] == 'Kid':
          url += '&channelSection=KIDS'
      #LOG(url)
      headers = self.net.headers.copy()
      if self.platform['use_nowtv_api']:
        headers['x-skyott-endorsements'] = 'videoFormat; caps="UHD",colorSpace; caps="HDR",audioFormat; caps="Stereo"'
      data = self.net.load_data(url, headers)
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
        t['channel_title'] = c.get('channelTitle')
        t['id'] = c['id']
        t['service_key'] = c['serviceKey']
        t['info']['playcount'] = 1 # Set as watched
        if 'images' in c:
          t['art'] = self.get_art(c['images'])
        t['channel_type'] = c['type']
        if 'contentSegments' in c:
          t['subscribed'] = self.is_subscribed(c['contentSegments'])
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
        if 'peacocktv' in data['host']:
          output_dir = 'peacocktv'
        elif 'nowtv.it' in data['host']:
          output_dir = 'nowtv-it'
        elif 'nowtv' in data['host']:
          output_dir = 'nowtv'
        elif 'wowtv' in data['host']:
          output_dir = 'wowtv'
        else:
          output_dir = 'skyshowtime'
        self.cache.save_file(output_dir + '/cookie.conf', data['data'])
        if 'device_id' in data:
          self.cache.save_file(output_dir + '/device_id.conf', data['device_id'])

    def export_key_file(self, directory, filename=None):
      if not filename:
        today = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
        filename = u'{}_{}.key'.format(self.platform['name'], today).encode('utf-8')
      if sys.version_info[0] > 2:
        directory = bytes(directory, 'utf-8')
      path = directory + filename
      data = {'app_name': 'skyott', 'timestamp': str(int(time.time()*1000)),
              'host': 'https://www.' + self.platform['host'],
              'data': self.account['cookie'].decode('utf-8'),
              'device_id': self.platform['device_id']}
      #print_json(data)
      with io.open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False))

    def install_cookie_file(self, filename):
      import shutil
      if sys.version_info[0] > 2:
        filename = bytes(filename, 'utf-8')
      shutil.copyfile(filename, self.cache.config_directory + self.pldir + '/cookie.conf')

    def clear_session(self):
      files = ['device_id.conf', 'localisation.json', 'profile.json', 'profile_info.json', 'token.json', 'menu.json', 'me.json']
      for f in files:
        self.cache.remove_file(self.pldir +'/'+ f)

    def save_credentials(self, username, password):
      from .b64 import encode_base64
      data = {'username': username, 'password': encode_base64(password)}
      self.cache.save_json(self.pldir + '/credentials.json', data)

    def load_credentials(self):
      from .b64 import decode_base64
      content = self.cache.load_file(self.pldir + '/credentials.json')
      if content:
        data = json.loads(content)
        return data['username'], decode_base64(data['password'])
      else:
        return '', ''

    def get_manifest_with_ads(self, playback_info):
      from .ads import get_fw_data, get_ad_url
      data = self.get_public_profile()
      profile_id = data['profile']['id']['obfuscatedids']['adobe_analytics']['profileid']
      fw_data = get_fw_data(profile_id, playback_info, self.account,
                            self.platform['headers']['x-skyott-territory'], self.net.headers,
                            self.platform['name'])
      #print_json(fw_data)
      data = get_ad_url(playback_info['manifest_url'], fw_data, self.net.headers, self.platform['name'])
      #print_json(data)
      if 'manifestUrl' in data:
        return data['manifestUrl'] #, data['trackingUrl']
      else:
        return None #, None

    @staticmethod
    def save_file(filename, content):
      if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False, indent=4)
      if sys.version_info[0] < 3:
        if not isinstance(content, unicode):
          content = unicode(content, 'utf-8')
      with io.open(filename, 'w', encoding='utf-8') as handle:
        handle.write(content)
