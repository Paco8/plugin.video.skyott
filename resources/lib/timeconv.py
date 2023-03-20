#!/usr/bin/env python
# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import sys
from datetime import datetime

def timestamp2str(timestamp, format='%H:%M'):
  time = datetime.fromtimestamp(timestamp)
  s = time.strftime(format).capitalize()
  if sys.version_info[0] < 3:
    s = s.decode('utf-8')
  return s
