#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import xbmc
from resources.lib.proxy import Proxy
from resources.lib.addon import *
from resources.lib.log import LOG

if __name__ == '__main__':
  LOG('Service started')
  proxy = Proxy()
  proxy.start()
  LOG('proxy_address: {}'.format(proxy.proxy_address))

  monitor = xbmc.Monitor()
  while not monitor.abortRequested():
    if monitor.waitForAbort(1):
      break

  proxy.stop()
