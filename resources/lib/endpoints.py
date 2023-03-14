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
    self.endpoints = {
      'section': webclients + '/bff/sections/v1?partition_id=no-partition&template=sections&segment=First_30_Days_Paid&slug={slug}',
      'get-series': atom + '/adapter-calypso/v3/query/node?slug={slug}&represent=(items(items))',
      'get-video-info': atom + '/adapter-calypso/v3/query/node?slug={slug}',
      'login': rango +'/signin/service/international',
      'profiles': webclients +'/bff/personas/v2',
      'select-profile': webclients + '/bff/personas/v2/{profile_id}?skipPinValidation=true',
      'my-stuff': webclients + '/bff/sections/v1?partition_id=no-partition&template=sections&segment=default&slug=%2Fmy-stuff',
      'my-list': webclients + '/bff/sections/v1/personalised?partition_id=no-partition&template=sections&segment=default&slug={slug}&filter=byw&filter=pg&filter=wl&filter=cw',
      'localisation': ovp + '/ls/localisation',
      'me': ovp + '/auth/users/me',
      'tokens': ovp + '/auth/throttled/tokens',
      'playouts': ovp + '/video/playouts/vod',
    }