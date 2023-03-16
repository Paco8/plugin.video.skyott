# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import sys
import json

import xbmc
import xbmcgui
import xbmcplugin

if sys.version_info[0] >= 3:
  import urllib.request as urllib2
  from urllib.parse import urlencode, parse_qsl, quote_plus
  unicode = str
else:
  import urllib2
  from urllib import urlencode, quote_plus
  from urlparse import parse_qsl

import xbmcaddon
import os.path

from .log import LOG
from .sky import *
from .addon import *
from .gui import *

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

def get_url(**kwargs):
  for key, value in kwargs.items():
    if isinstance(value, unicode):
      kwargs[key] = value.encode('utf-8')
  return '{0}?{1}'.format(_url, urlencode(kwargs))

def play(slug):
  LOG('play - slug: {}'.format(slug))

  data = sky.get_video_info(slug)
  LOG('video info: {}'.format(data))
  if not 'content_id' in data:
    show_notification('No content id')
    return

  data = sky.get_playback_info(data['content_id'], data['provider_variant_id'])
  LOG('playback info: {}'.format(data))
  if not data.get('manifest_url'):
    show_notification('No playback url')
    return

  import inputstreamhelper
  is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
  if not is_helper.check_inputstream():
    show_notification(addon.getLocalizedString(30202))
    return

  proxy = sky.cache.load_file('proxy.conf')
  if not proxy:
    show_notification('Proxy is not running')
    return

  play_item = xbmcgui.ListItem(path=data['manifest_url'])
  play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
  play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
  license_url = '{}/license?url={}||R{{SSM}}|'.format(proxy, quote_plus(data['license_url']))
  LOG('license_url: {}'.format(license_url))
  play_item.setProperty('inputstream.adaptive.license_key', license_url)
  #play_item.setProperty('inputstream.adaptive.stream_headers', 'User-Agent=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0')
  #play_item.setProperty('inputstream.adaptive.server_certificate', certificate)
  #play_item.setProperty('inputstream.adaptive.license_flags', 'persistent_storage')
  #play_item.setProperty('inputstream.adaptive.license_flags', 'force_secure_decoder')

  if sys.version_info[0] < 3:
    play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
  else:
    play_item.setProperty('inputstream', 'inputstream.adaptive')

  play_item.setMimeType('application/dash+xml')
  play_item.setContentLookup(False)
  xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

def add_videos(category, ctype, videos, ref=None, url_next=None, url_prev=None):
  #LOG("category: {} ctype: {}".format(category, ctype))
  xbmcplugin.setPluginCategory(_handle, category)
  xbmcplugin.setContent(_handle, ctype)

  if ctype == 'movies' or ctype == 'seasons':
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_TITLE)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_GENRE)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LASTPLAYED)
  if ctype == 'episodes':
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_EPISODE)

  """
  if url_prev:
    list_item = xbmcgui.ListItem(label = addon.getLocalizedString(30110)) # Previous page
    xbmcplugin.addDirectoryItem(_handle, get_url(action=ref, url=url_prev, name=category), list_item, True)
  """

  for t in videos:
    #LOG("t: {}".format(t))
    title_name = t['info']['title']
    if not 'type' in t: continue
    if t['type'] == 'movie':
      list_item = xbmcgui.ListItem(label = title_name)
      list_item.setProperty('IsPlayable', 'true')
      list_item.setInfo('video', t['info'])
      list_item.setArt(t['art'])
      url = get_url(action='play', slug=t['slug'])
      xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    elif t['type'] == 'series':
      list_item = xbmcgui.ListItem(label = title_name)
      list_item.setInfo('video', t['info'])
      list_item.setArt(t['art'])
      xbmcplugin.addDirectoryItem(_handle, get_url(action='series', slug=t['slug'], name=title_name), list_item, True)
    elif t['type'] == 'season':
      list_item = xbmcgui.ListItem(label = title_name)
      list_item.setInfo('video', t['info'])
      list_item.setArt(t['art'])
      xbmcplugin.addDirectoryItem(_handle, get_url(action='season', slug=t['slug'], name=title_name), list_item, True)
    elif t['type'] == 'category':
      list_item = xbmcgui.ListItem(label = title_name)
      #list_item.setInfo('video', t['info'])
      #list_item.setArt(t['art'])
      xbmcplugin.addDirectoryItem(_handle, get_url(action='category', slug=t['slug'], name=title_name), list_item, True)

  if url_next:
    list_item = xbmcgui.ListItem(label = addon.getLocalizedString(30109)) # Next page
    xbmcplugin.addDirectoryItem(_handle, get_url(action=ref, url=url_next, name=category), list_item, True)

  xbmcplugin.endOfDirectory(_handle)

def list_profiles(params):
  LOG('list_profiles: params: {}'.format(params))
  profiles = sky.get_profiles()

  if 'id' in params:
    if params['name'] == 'select':
      LOG('Selecting profile {}'.format(params['id']))
      sky.change_profile(params['id'])
    xbmc.executebuiltin("Container.Refresh")
    return

  open_folder(addon.getLocalizedString(30180)) # Profiles
  for p in profiles:
    name = p['name']
    if p['id'] == sky.account['profile_id']:
      name = '[B][COLOR blue]' + name + '[/COLOR][/B]'
    img_url = p['avatar']
    art = {'icon': img_url} if img_url else None
    select_action = get_url(action='profiles', id=p['id'], name='select')
    add_menu_option(name, select_action, art=art)
  close_folder(cacheToDisc=False)

def search(params):
  search_term = params.get('search_term', None)
  if search_term:
    if sys.version_info[0] < 3:
      search_term = search_term.decode('utf-8')
    if params.get('name', None) == 'delete':
      sky.delete_search(search_term)
      xbmc.executebuiltin("Container.Refresh")
    else:
      videos = sky.search_vod(search_term)
      add_videos(addon.getLocalizedString(30117), 'movies', videos)
    return

  if params.get('name', None) == 'new':
    search_term = input_window(addon.getLocalizedString(30116)) # Search term
    if search_term:
      if sys.version_info[0] < 3:
        search_term = search_term.decode('utf-8')
      sky.add_search(search_term)
    xbmc.executebuiltin("Container.Refresh")
    return

  open_folder(addon.getLocalizedString(30113)) # Search
  add_menu_option(addon.getLocalizedString(30113), get_url(action='search', name='new')) # New search

  for i in sky.search_list:
    remove_action = get_url(action='search', search_term=i, name='delete')
    cm = [(addon.getLocalizedString(30114), "RunPlugin(" + remove_action + ")")]
    add_menu_option(i.encode('utf-8'), get_url(action='search', search_term=i), cm)

  close_folder(cacheToDisc=False)

def clear_session():
  LOG('clear_session')
  files = ['device_id.conf', 'localisation.json', 'profile_id.conf', 'token.json']
  for f in files:
    sky.cache.remove_file(sky.pldir +'/' + f)

def logout():
  clear_session()
  sky.delete_cookie()

def login():
  def ask_credentials(username=''):
    username = input_window(addon.getLocalizedString(30163), username) # Username
    if username:
      password = input_window(addon.getLocalizedString(30164), hidden=True) # Password
      if password:
        return username, password
    return None, None

  username, password = ask_credentials()
  if username:
    success, _ = sky.login(username, password)
    if success:
      clear_session()
    else:
      show_notification(addon.getLocalizedString(30166)) # Failed

def list_users():
  open_folder(addon.getLocalizedString(30160)) # Change user
  add_menu_option(addon.getLocalizedString(30183), get_url(action='login')) # Login with username
  add_menu_option(addon.getLocalizedString(30150), get_url(action='logout')) # Close session
  close_folder()


def router(paramstring):
  """
  Router function that calls other functions
  depending on the provided paramstring
  :param paramstring: URL encoded plugin paramstring
  :type paramstring: str
  """

  params = dict(parse_qsl(paramstring))
  LOG('params: {}'.format(params))
  if params:
    if params['action'] == 'play':
      play(params['slug'])
    elif params['action'] == 'profiles':
      list_profiles(params)
    elif params['action'] == 'login':
      login()
    elif params['action'] == 'user':
      list_users()
    elif params['action'] == 'logout':
      logout()
    elif params['action'] == 'wishlist':
      add_videos(addon.getLocalizedString(30102), 'movies', sky.get_my_list())
    elif params['action'] == 'category':
      add_videos(params['name'], 'movies', sky.get_catalog(params['slug']))
    elif params['action'] == 'movie_catalog':
      name = addon.getLocalizedString(30105).encode('utf-8')
      add_videos(name, 'movies', sky.get_movie_catalog())
    elif params['action'] == 'series_catalog':
      name = addon.getLocalizedString(30106).encode('utf-8')
      add_videos(name, 'movies', sky.get_series_catalog())
    elif params['action'] == 'series':
      add_videos(params['name'], 'seasons', sky.get_seasons(params['slug']))
    elif params['action'] == 'season':
      add_videos(params['name'], 'episodes', sky.get_episodes(params['slug']))
    elif params['action'] == 'search':
      search(params)
  else:
    # Main
    open_folder(addon.getLocalizedString(30101)) # Menu
    xbmcplugin.setContent(_handle, 'files')

    for item in sky.get_main_menu():
      if item['id'] == 'My Stuff' and sky.logged:
        add_menu_option(item['title'], get_url(action='wishlist')) # My list
      else:
        add_menu_option(item['title'], get_url(action='category', name=item['title'], slug=item['slug']))

    add_menu_option(addon.getLocalizedString(30112), get_url(action='search')) # Search

    if sky.logged:
      add_menu_option(addon.getLocalizedString(30180), get_url(action='profiles')) # Profiles
      #add_menu_option(addon.getLocalizedString(30108), get_url(action='devices')) # Devices

    add_menu_option(addon.getLocalizedString(30160), get_url(action='user')) # Accounts
    close_folder(cacheToDisc=False)


def run():
  global sky
  LOG('profile_dir: {}'.format(profile_dir))
  platform_id = addon.getSetting('platform_id')
  LOG('platform_id: {}'.format(platform_id))
  sky = SkyShowtime(profile_dir, platform_id)

  # Clear cache
  LOG('Cleaning cache. {} files removed.'.format(sky.cache.clear_cache()))

  # Call the router function and pass the plugin call parameters to it.
  # We use string slicing to trim the leading '?' from the plugin call paramstring
  params = sys.argv[2][1:]
  router(params)
