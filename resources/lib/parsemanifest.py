#!/usr/bin/env python
# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import re
import os
import requests
from .log import LOG

def download_split_subtitle(base_url, filename_template, start_number=0):
  session = requests.Session()
  filename_template = filename_template.replace('$Number$', '{}')
  i = start_number
  res = []
  while True:
    url = os.path.join(base_url, filename_template.format(i))
    LOG('Downloading {}'.format(url))
    response = session.get(url)
    if response.status_code == 404:
        break
    res.append(response.content.decode('utf-8'))
    i += 1
  return ''.join(res)

def extract_tracks(manifest):
  pattern = re.compile(r'<AdaptationSet.*?</AdaptationSet>', re.DOTALL)
  matches = re.findall(pattern, manifest)
  tracks = {'audios': [], 'subs': []}
  for track in matches:
    t = {'orig': track}
    for label in ['contentType', 'Label', 'lang', 'mimeType', 'value', 'codecs']:
      m = re.search(r'{}="(.*?)"'.format(label), track, re.DOTALL)
      t[label] = m.group(1) if m else ''
    m = re.search(r'<BaseURL>(.*?)</BaseURL>', track, re.DOTALL)
    t['split'] = False
    t['filename'] = m.group(1) if m else ''
    if 'AdaptationSet' in track:
      m = re.search(r'media="([^"]+)"\s+startNumber="([^"]+)"', track)
      if m:
        t['split'] = True
        t['filename'] = m.group(1)
        t['start_number'] = m.group(2)
    if t['contentType'] in ['text', 'audio']:
      #new_lang = t['lang'][:2]
      new_lang = re.sub(r'-[A-Z]{2}', '', t['lang'])
      if t['value'] == 'caption': new_lang += '-[CC]'
      if t['value'] == 'forced-subtitle': new_lang += '-[Forced]'
      t['new_lang'] = new_lang
      t['mod'] = track.replace('lang="{}"'.format(t['lang']), 'lang="{}"'.format(new_lang))
    if t['contentType'] == 'text':
      tracks['subs'].append(t)
    elif t['contentType'] == 'audio':
      tracks['audios'].append(t)
  return tracks
