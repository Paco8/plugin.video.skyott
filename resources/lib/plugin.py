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
from .user_agent import chrome_user_agent

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

def get_url(**kwargs):
  for key, value in kwargs.items():
    if isinstance(value, unicode):
      kwargs[key] = value.encode('utf-8')
  return '{0}?{1}'.format(_url, urlencode(kwargs))

def play(params):
  slug = params.get('slug')
  service_key = params.get('service_key')

  LOG('play - slug: {} service_key: {}'.format(slug, service_key))

  if sky.platform['name'] == 'SkyShowtime':
    if 'NO_ADS' not in sky.account['account_type']:
      show_notification(addon.getLocalizedString(30209))
      return

  if slug:
    info = sky.get_video_info(slug)
    LOG('video info: {}'.format(info))
    if not 'content_id' in info:
      show_notification('No content id')
      return

  preferred_server = addon.getSetting('preferred_server')
  enable_uhd = addon.getSettingBool('uhd')
  dolbyvision = addon.getSettingBool('dolbyvision')
  hdr10 = addon.getSettingBool('hdr10')
  enable_hdcp = bool(addon.getSettingBool('hdcp_enabled'))
  if slug:
    data = sky.get_playback_info(info['content_id'], info['provider_variant_id'], preferred_server, uhd=enable_uhd, hdcpEnabled=enable_hdcp, dolbyvision=dolbyvision, hdr10=hdr10)
  else:
    if params.get('content_id') and params.get('provider_variant_id'):
      data = sky.get_playback_info(params['content_id'], params['provider_variant_id'], preferred_server, hdcpEnabled=enable_hdcp)
    else:
      data = sky.get_live_playback_info(service_key, preferred_server, hdcpEnabled=enable_hdcp)

  LOG('playback info: {}'.format(data))
  if not 'manifest_url' in data:
    if 'errorCode' in data['response']:
      show_notification(data['response']['description'])
    else:
      show_notification(addon.getLocalizedString(30205)) # No playback url
    return

  import inputstreamhelper
  is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
  if not is_helper.check_inputstream():
    show_notification(addon.getLocalizedString(30202))
    return

  proxy = sky.cache.load_file('proxy.conf')
  if not proxy:
    show_notification(addon.getLocalizedString(30206)) # Proxy is not running
    return

  url = data['manifest_url']
  if addon.getSettingBool('manifest_modification'):
    url = '{}/?manifest={}'.format(proxy, url)

  #url = 'http://ftp.itec.aau.at/datasets/DASHDataset2014/BigBuckBunny/10sec/BigBuckBunny_10s_onDemand_2014_05_09.mpd'
  #url = 'https://rdmedia.bbc.co.uk/bbb/2/client_manifest-common_init.mpd'

  play_item = xbmcgui.ListItem(path=url)
  play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
  play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
  if 'license_url' in data:
    license_url = '{}/license?url={}||R{{SSM}}|'.format(proxy, quote_plus(data['license_url']))
    LOG('license_url: {}'.format(license_url))
    play_item.setProperty('inputstream.adaptive.license_key', license_url)
  play_item.setProperty('inputstream.adaptive.stream_headers', 'User-Agent=' + chrome_user_agent)
  #play_item.setProperty('inputstream.adaptive.server_certificate', certificate)
  #play_item.setProperty('inputstream.adaptive.license_flags', 'persistent_storage')
  #play_item.setProperty('inputstream.adaptive.license_flags', 'force_secure_decoder')

  if sys.version_info[0] < 3:
    play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
  else:
    play_item.setProperty('inputstream', 'inputstream.adaptive')

  play_item.setMimeType('application/dash+xml')
  try:
    play_item.setInfo('video', info['info'])
    play_item.setArt(info['art'])
  except:
    pass

  if addon.getSettingBool('use_ttml2ssa') and slug:
    # Convert subtitles
    import re
    from .parsemanifest import extract_tracks, download_split_subtitle
    from ttml2ssa import Ttml2SsaAddon
    ttml = Ttml2SsaAddon()
    subtype = ttml.subtitle_type()

    subfolder = profile_dir + 'subtitles/'
    if not os.path.exists(subfolder):
      os.makedirs(subfolder)

    response = sky.net.session.get(data['manifest_url'], allow_redirects=True)
    content = response.content.decode('utf-8')
    #LOG(content)
    baseurl = os.path.dirname(response.url)

    subpaths = []
    tracks = extract_tracks(content)
    filter_list = addon.getSetting('ttml2ssa_filter').lower().split()
    subtracks = []
    if len(filter_list) > 0:
      subtracks = [t for t in tracks['subs'] if t['lang'][:2] in filter_list]
    for t in subtracks:
      filename = subfolder + t['lang'][:2]
      if t['value'] == 'caption': filename += ' [CC]'
      elif t['value'] == 'forced-subtitle': filename += '.forced'
      LOG('filename: {}'.format(filename))

      if not addon.getSettingBool('include_forced_subs') and '.forced' in filename:
        continue

      if not addon.getSettingBool('include_non_forced_subs') and not '.forced' in filename:
        continue

      if t['split']:
        content = download_split_subtitle(baseurl, t['filename'], int(t['start_number']))
      else:
        content = sky.net.load_url(os.path.join(baseurl, t['filename']))

      # Add <i> and </i> for italics
      content = re.sub(r'<c\.[^>]*font-style_italic[^>]*>(.*?)<\/c>', r'<i>\1</i>', content, flags=re.DOTALL)
      # Remove remaining <c> tags
      content = re.sub(r'<c\.[^>]*>|<\/c>', '', content)
      # Add spaces before and after <i> </i> if necessary
      content = re.sub(r'(?<![!¿?\-\s])<i>', r' <i>', content)
      content = re.sub(r'</i>(?![.,;:!?\-\s])', r'</i> ', content)

      #LOG(content.encode('utf-8'))
      ttml.parse_vtt_from_string(content)
      if subtype != 'srt':
        filename_ssa = filename + '.ssa'
        ttml.write2file(filename_ssa)
        subpaths.append(filename_ssa)
      if subtype != 'ssa':
        filename_srt = filename
        if (subtype == 'both'): filename_srt += '.SRT'
        filename_srt += '.srt'
        ttml.write2file(filename_srt)
        subpaths.append(filename_srt)
    play_item.setSubtitles(subpaths)

  play_item.setContentLookup(False)
  xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

  # Control player
  send_progress = addon.getSettingBool('send_progress')
  skip_recap = addon.getSettingBool('skip_recap')
  skip_intro = addon.getSettingBool('skip_intro')
  LOG('markers: {}'.format(info.get('markers')))
  if (send_progress or skip_recap or skip_intro) and slug:
    from .player import SkyPlayer
    player = SkyPlayer()
    monitor = xbmc.Monitor()

    def check_marker(l_start, l_end, last_pos):
      if l_start in info['markers'] and l_end in info['markers']:
        s_start = int(info['markers'][l_start] / 1000)
        s_end = int(info['markers'][l_end] / 1000) - 2
        #LOG('s_start: {} s_end: {}'.format(s_start, s_end))
        if last_pos > s_start:
          if s_end - s_start > 10:
            player.seekTime(s_end)
          del info['markers'][l_start]
      return

    if send_progress:
      last_pos = 0
      total_time = 0
      start_time = time.time()
      interval = addon.getSettingInt('progress_interval')
      if interval < 20: interval = 20
      LOG('progress_interval: {}'.format(interval))
    while not monitor.abortRequested() and player.running:
      monitor.waitForAbort(2)
      if player.isPlaying():
        last_pos = player.getTime()
        if send_progress:
          if total_time == 0: total_time = player.getTotalTime()
          #LOG('**** position: {}'.format(last_pos))
          if time.time() > (start_time + interval):
            start_time = time.time()
            LOG('**** {} {}'.format(info['provider_variant_id'], info['bookmark_metadata']))
            sky.set_bookmark(info['provider_variant_id'], info['bookmark_metadata'], last_pos)
        if 'markers' in info:
          if skip_recap: check_marker('SOR', 'EOR', last_pos)
          if skip_intro: check_marker('SOI', 'EOI', last_pos)
    LOG('**** playback finished')
    if send_progress:
      LOG('**** last_pos: {} total_time: {}'.format(last_pos, total_time))
      if (total_time - last_pos) < 20: last_pos = total_time
      if last_pos > interval:
        sky.set_bookmark(info['provider_variant_id'], info['bookmark_metadata'], last_pos)


def add_videos(category, ctype, videos, from_watchlist=False, from_continue=False, updateListing=False, cacheToDisc=True):
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

  for t in videos:
    #LOG("t: {}".format(t))

    if t.get('subscribed', True) == False:
      if addon.getSettingBool('only_subscribed'): continue
      t['info']['title'] = '[COLOR gray]' + t['info']['title'] + '[/COLOR]'

    if 'offer' in t:
      ends = t['offer'].get('end', 0)
      if ends > 0:
        now = int(time.time()*1000)
        n_hours = int((ends - now) / (1000 * 60 * 60))
        n_days = int(n_hours / 24)
        if (n_days <= 30):
          if n_days < 1:
            t['info']['title'] += ' [COLOR red](' + addon.getLocalizedString(30401).format(n_hours) + ')[/COLOR]'
          else:
            t['info']['title'] += ' [COLOR red](' + addon.getLocalizedString(30400).format(n_days) + ')[/COLOR]'

    title_name = t['info']['title']
    if not 'type' in t: continue

    # Fix art
    if 'mediatype' in t['info'] and 'art' in t:
      if t['info']['mediatype'] != 'episode':
        t['art']['thumb'] = t['art'].get('poster')
      if t['info']['mediatype'] == 'episode':
        t['art']['fanart'] = None

    menu_items = []
    if t['type'] in ['movie', 'series'] and 'slug' in t:
      if not from_watchlist:
        menu_items.append((addon.getLocalizedString(30175), "RunPlugin(" + get_url(action='to_watchlist', slug=t['slug'], op='add') + ")"))
      else:
        menu_items.append((addon.getLocalizedString(30176), "RunPlugin(" + get_url(action='to_watchlist', slug=t['slug'], op='delete') + ")"))
    if from_continue and t.get('info', []).get('mediatype') == 'movie':
        menu_items.append((addon.getLocalizedString(30179), "RunPlugin(" + get_url(action='remove_from_continue', slug=t['slug']) + ")"))

    if t['type'] == 'movie':
      # If an episode is not in a episode listing, display the series name too
      if ctype != 'episodes' and t['info'].get('mediatype', '') == 'episode':
        t['info']['title'] = '{} {}x{} - {}'.format(t['info'].get('tvshowtitle', ''), t['info'].get('season', 0), t['info'].get('episode', 0), t['info']['title'])
      list_item = xbmcgui.ListItem(label = title_name)
      list_item.setProperty('IsPlayable', 'true')
      if addon.getSettingBool('send_progress') and 'stream_position' in t:
        list_item.setProperty('ResumeTime', str(t['stream_position']))
        list_item.setProperty('TotalTime', str(t['info']['duration']))
      list_item.setInfo('video', t['info'])
      list_item.setArt(t['art'])
      if t.get('stream_type') == 'tv':
        url = get_url(action='play', service_key=t['service_key'])
        if 'content_id' in t and 'provider_variant_id' in t:
          url += '&content_id={}&provider_variant_id={}'.format(t['content_id'], t['provider_variant_id'])
      else:
        url = get_url(action='play', slug=t['slug'])
      if len(menu_items) > 0:
        list_item.addContextMenuItems(menu_items)
      xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    elif t['type'] == 'series':
      list_item = xbmcgui.ListItem(label = title_name)
      list_item.setInfo('video', t['info'])
      list_item.setArt(t['art'])
      if len(menu_items) > 0:
        list_item.addContextMenuItems(menu_items)
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

  xbmcplugin.endOfDirectory(_handle, updateListing=updateListing, cacheToDisc=cacheToDisc)

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
      videos = sky.search(search_term)
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
  sky.clear_session()

def logout():
  clear_session()
  sky.delete_cookie()

def login():
  def ask_credentials(username='', password=''):
    username = input_window(addon.getLocalizedString(30163), username) # Username
    if username:
      password = input_window(addon.getLocalizedString(30164), password, hidden=True) # Password
      if password:
        return username, password
    return None, None

  store_credentials = addon.getSettingBool('store_credentials')
  if store_credentials:
    username, password = sky.load_credentials()
  else:
    username, password = ('', '')

  username, password = ask_credentials(username, password)
  if username:
    if store_credentials:
      sky.save_credentials(username, password)
    success, _ = sky.login(username, password)
    if success:
      clear_session()
      show_notification(addon.getLocalizedString(30168), xbmcgui.NOTIFICATION_INFO) # Success
    else:
      show_notification(addon.getLocalizedString(30166)) # Failed

def login_with_key():
  filename = xbmcgui.Dialog().browseSingle(1, addon.getLocalizedString(30182), '', '.key')
  if filename:
    clear_session()
    sky.import_key_file(filename)

def login_with_cookie():
  filename = xbmcgui.Dialog().browseSingle(1, addon.getLocalizedString(30187), '', '.txt|.conf')
  if filename:
    sky.install_cookie_file(filename)
    clear_session()

def export_key():
  directory = xbmcgui.Dialog().browseSingle(0, addon.getLocalizedString(30185), '')
  LOG('type directory: {}'.format(type(directory)))
  if directory:
    sky.export_key_file(directory)

def list_users():
  platform_name = addon.getSetting('platform_id')
  open_folder(addon.getLocalizedString(30160)) # Accounts
  add_menu_option(addon.getLocalizedString(30191).format(platform_name), get_url(action='login', method='credentials')) # Login with username
  add_menu_option(addon.getLocalizedString(30190).format(platform_name), get_url(action='login', method='key')) # Login with key
  #add_menu_option(addon.getLocalizedString(30186), get_url(action='login', method='cookie')) # Login with cookie
  if sky.account['cookie']:
    add_menu_option(addon.getLocalizedString(30184), get_url(action='export_key')) # Export key
  add_menu_option(addon.getLocalizedString(30150), get_url(action='logout')) # Close session
  close_folder()

def list_platforms():
  platforms = ['SkyShowtime', 'PeacockTV']
  open_folder(addon.getLocalizedString(30160)) # Accounts
  for platform in platforms:
    name = addon.getLocalizedString(30192).format(platform)
    if platform == addon.getSetting('platform_id'):
      name = '[B][COLOR blue]' + name + '[/COLOR][/B]'
    add_menu_option(name, get_url(action='select_platform', platform=platform))
  close_folder()

def to_watchlist(params):
  retcode, message = sky.to_watchlist(slug=params['slug'], action=params['op'])
  if retcode == 201:
    message = 30177 if params['op'] == 'add' else 30178
    show_notification(addon.getLocalizedString(message), xbmcgui.NOTIFICATION_INFO)
    if params['op'] == 'delete':
      xbmc.executebuiltin("Container.Refresh")
  else:
    show_notification(str(retcode) +': '+ message)

def remove_from_continue(params):
  info = sky.get_video_info(params['slug'])
  LOG('remove_from_continue: info: {}'.format(info))
  status_code = sky.set_bookmark(info['provider_variant_id'], info['bookmark_metadata'], info['info']['duration'])
  LOG('status_code: {}'.format(status_code))
  xbmc.executebuiltin("Container.Refresh")

def list_devices(params):
  LOG('list_devices: params: {}'.format(params))

  devices = sky.get_devices()

  if 'id' in params:
    if params['name'] == 'select':
      LOG('Selecting device {}'.format(params['id']))
      #sky.change_device(params['id'])
    xbmc.executebuiltin("Container.Refresh")
    return

  open_folder(addon.getLocalizedString(30108)) # Devices

  for d in devices:
    name = '{} {} {} ({})'.format(d['description'], d['alias'], d['str_date'], d['id'][:8])
    if d['id'] in sky.account['cookie']:
      name = '[B][COLOR blue]' + name + '[/COLOR][/B]'

    select_action = get_url(action='devices', id=d['id'], name='select')
    add_menu_option(name, select_action)

  close_folder(cacheToDisc=False)


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
      play(params)
    elif params['action'] == 'profiles':
      list_profiles(params)
    elif params['action'] == 'login':
      if params['method'] == 'key':
        login_with_key()
      elif params['method'] == 'cookie':
        login_with_cookie()
      else:
        login()
    elif params['action'] == 'export_key':
      export_key()
    elif params['action'] == 'user':
      list_users()
    elif params['action'] == 'logout':
      logout()
    elif params['action'] == 'platforms':
      list_platforms()
    elif params['action'] == 'select_platform':
      addon.setSetting('platform_id', params['platform'])
      list_users()
    elif params['action'] == 'wishlist':
      add_videos(addon.getLocalizedString(30102), 'movies', sky.get_my_list(), from_watchlist=True)
    elif params['action'] == 'continue-watching':
      add_videos(addon.getLocalizedString(30122), 'movies', sky.get_continue_watching(), from_continue=True, cacheToDisc=False)
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
    elif params['action'] == 'tv':
      add_videos(addon.getLocalizedString(30104), 'movies', sky.get_channels_with_epg())
    elif params['action'] == 'to_watchlist':
      to_watchlist(params)
    elif params['action'] == 'remove_from_continue':
      remove_from_continue(params)
    elif params['action'] == 'devices':
      list_devices(params)
  else:
    # Main
    open_folder(addon.getLocalizedString(30101)) # Menu
    xbmcplugin.setContent(_handle, 'files')

    if sky.logged:
      for item in sky.get_main_menu():
        if item['id'] == 'My Stuff':
          add_menu_option(item['title'], get_url(action='wishlist'), icon='mylist.png') # My list
        elif item['id'] == 'Channels':
          add_menu_option(item['title'], get_url(action='tv'), icon='tv.png') # TV
        else:
          art = None
          #if item.get('icon'): art={'icon': item['icon']}
          add_menu_option(item['title'], get_url(action='category', name=item['title'], slug=item['slug']), art=art)

      add_menu_option(addon.getLocalizedString(30122), get_url(action='continue-watching'), icon='continue.png') # Continue watching
      add_menu_option(addon.getLocalizedString(30112), get_url(action='search'), icon='search.png') # Search
      add_menu_option(addon.getLocalizedString(30180), get_url(action='profiles'), icon='profiles.png') # Profiles
      #add_menu_option(addon.getLocalizedString(30108), get_url(action='devices')) # Devices

    #add_menu_option(addon.getLocalizedString(30160), get_url(action='user')) # Accounts
    add_menu_option(addon.getLocalizedString(30160), get_url(action='platforms'), icon='account.png') # Accounts
    close_folder(cacheToDisc=False)


def run():
  # Call the router function and pass the plugin call parameters to it.
  # We use string slicing to trim the leading '?' from the plugin call paramstring
  params = sys.argv[2][1:]

  if 'show_donation_dialog' in params:
    from .customdialog import show_donation_dialog
    show_donation_dialog()
    return

  global sky
  LOG('profile_dir: {}'.format(profile_dir))
  platform_id = addon.getSetting('platform_id').lower()
  LOG('platform_id: {}'.format(platform_id))
  territory = addon.getSetting('territory').upper()
  LOG('territory: {}'.format(territory))
  sky = SkyShowtime(profile_dir, platform_id, territory)

  if sky.logged and not sky.account['user_token']:
    show_notification(addon.getLocalizedString(30207) +': '+ sky.get_token_error)

  # Clear cache
  LOG('Cleaning cache. {} files removed.'.format(sky.cache.clear_cache()))

  router(params)
