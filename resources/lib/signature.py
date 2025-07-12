#!/usr/bin/env python
# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import base64
import hmac
import hashlib
import sys
import time

if sys.version_info[0] >= 3:
  from urllib.parse import urlparse
else:
  from urlparse import urlparse


class Signature(object):

  platforms = {
      'peacocktv': {
          'app_id': 'NBCU-ANDROID-v3',
          'signature_key': bytearray('SnVMUWd5Rno5bjg5RDlweGNONlpXWlhLV2ZnajJQTkJVYjMyenliag==', 'utf-8'),
          'version': '1.0'
      },
      'skyshowtime': {
          'app_id': 'SKYSHOWTIME-ANDROID-v1',
          'signature_key': bytearray('amZqOXFHZzZhREhhQmJGcEg2d05Fdk42Y0h1SHRaVnBwSFJ2Qmdacw==', 'utf-8'),
          'version': '1.0'
      },
      'nowtv': {
          'app_id': 'IE-NOWTV-ANDROID-v1',
          'signature_key': bytearray('NWY4UkxCcHBhcUtHTzhid0t3Tmlmalo2Yk04elhDVndrQUs3aGtocTNQUzRwZg==', 'utf-8'),
          'version': '1.0'
      }
  }

  def __init__(self, platform='skyshowtime'):
    self.platform = platform
    if platform in ['wowtv', 'nowtv', 'nowtv-it']:
      self.app_id = self.platforms['nowtv']['app_id']
      self.signature_key = self.platforms['nowtv']['signature_key']
      self.sig_version = self.platforms['nowtv']['version']
    else:
      self.app_id = self.platforms[platform]['app_id']
      self.signature_key = self.platforms[platform]['signature_key']
      self.sig_version = self.platforms[platform]['version']

  def calculate_signature(self, method, url, headers, payload='', timestamp=None):
    if not timestamp:
      timestamp = int(time.time())

    if url.startswith('http'):
      parsed_url = urlparse(url)
      path = parsed_url.path
    else:
      path = url

    #print('path: {}'.format(path))

    text_headers = ''
    for key in sorted(headers.keys()):
      if key.lower().startswith('x-skyott'):
        text_headers += key.lower() + ': ' + headers[key] + '\n'
    #print(text_headers)
    headers_md5 = hashlib.md5(text_headers.encode()).hexdigest()
    #print(headers_md5)

    if sys.version_info[0] > 2 and isinstance(payload, str):
      payload = payload.encode('utf-8')
    payload_md5 = hashlib.md5(payload).hexdigest()

    to_hash = ('{method}\n{path}\n{response_code}\n{app_id}\n{version}\n{headers_md5}\n'
              '{timestamp}\n{payload_md5}\n').format(method=method, path=path,
                response_code='', app_id=self.app_id, version=self.sig_version,
                headers_md5=headers_md5, timestamp=timestamp, payload_md5=payload_md5)
    #print(to_hash)

    hashed = hmac.new(base64.b64decode(self.signature_key), to_hash.encode('utf8'), hashlib.sha1).digest()
    signature = base64.b64encode(hashed).decode('utf8')

    return {'x-sky-signature': 'SkyOTT client="{}",signature="{}",timestamp="{}",version="{}"'.format(
        self.app_id, signature, timestamp, self.sig_version)}

