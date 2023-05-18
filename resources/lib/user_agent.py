# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

chrome_user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'

def user_agent(platform='skyshowtime'):
  if platform == 'skyshowtime':
    return 'SkyShowtimeAndroid-GLOBAL/4.2.12-121040212'
  else:
    return 'PeacockAndroid-US/4.3.22-121040322'
