# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

def user_agent(platform='skyshowtime'):
  if platform == 'skyshowtime':
    return 'SkyShowtimeAndroid-GLOBAL/4.2.12-121040212'
  else:
    return 'PeacockAndroid-US/4.3.22-121040322'
