# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

class Endpoints(object):

  host = ''

  def __init__(self, host='skyshowtime.com'):
    self.host = host
    webclients = 'https://web.clients.' + self.host
    atom = 'https://atom.' + self.host
    rango = 'https://rango.id.' + self.host
    ovp = 'https://ovp.' + self.host
    cybertron = 'https://cybertron.id.'+ self.host
    if host == 'skyshowtime.com':
      mytv = 'https://mytv.clients.skyshowtime.com'
    elif host == 'nowtv.com':
      mytv = 'https://mytv.clients.nowtv.com'
      atom = 'https://eu.api.atom.nowtv.com'
    else:
      mytv = 'https://sas.peacocktv.com/mytv'
    self.endpoints = {
      'section': webclients + '/bff/sections/v1?partition_id=no-partition&template=sections&segment=all_premium_users&slug={slug}',
      'get-series': atom + '/adapter-calypso/v3/query/node?slug={slug}&represent=(items(items))',
      'get-video-info': atom + '/adapter-calypso/v3/query/node?slug={slug}',
      'get-video-info-uuid': atom + '/adapter-calypso/v3/query/nodes/uuid/{uuid}?exclude=expired%2Cfuture%2Cshortform',
      'login': rango +'/signin/service/international',
      'profiles': webclients +'/bff/personas/v2',
      'get-profile-info': webclients + '/bff/personas/v2/{profile_id}?skipPinValidation=true',
      'my-stuff': webclients + '/bff/sections/v1?partition_id=no-partition&template=sections&segment=all_premium_users&slug={slug}',
      'my-section': webclients + '/bff/sections/v1/personalised?partition_id=no-partition&template=sections&segment=all_premium_users&slug={slug}&filter=byw&filter=pg&filter=wl&filter=cw',
      'localisation': ovp + '/ls/localisation',
      'me': ovp + '/auth/users/me',
      'tokens': ovp + '/auth/throttled/tokens',
      'playouts': ovp + '/video/playouts/vod',
      'search-vod': 'https://suggest.disco.' + self.host + '/suggest/v1/stb/home/0/0/0?term={search_term}&limit=40&entitytype=programme&entitytype=series&contentFormat=longform',
      'search': webclients + '/bff/search/v2?term={search_term}&limit=40&entityType=programme%2Cseries&contentFormat=longform',
      'menu': atom + '/adapter-calypso/v3/query/menu',
      'epg': webclients + '/bff/channel_guide?startTime={start_time}',
      'playouts-live': ovp + '/video/playouts/live',
      'to-watchlist': mytv + '/watchlist/{uuid}',
      'get-bookmarks': ovp + '/bookmarking/bookmarks',
      'set-bookmark': ovp + '/bookmarking/bookmarks/{content_id}',
      'set-bookmark2': ovp + '/bookmarking-services/bookmarks/{content_id}',
      'get-devices': cybertron +'/sessions/me/devices',
      'get-public-profile': cybertron +'/public/profile',
      'get-rails': webclients + '/bff/browse/v1/rails/{id}?full_top_tiles=100&mode=GRID&segment=all_premium_users',
      'browse-page': webclients + '/bff/browse/v1/pages/{id}?segment=only_ge&full_top_rails=6&full_top_tiles=10'
    }
