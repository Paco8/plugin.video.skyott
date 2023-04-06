#!/usr/bin/env python
# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division

import re

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
    t['baseurl'] = m.group(1) if m else ''
    if t['contentType'] in ['text', 'audio']:
      new_lang = t['lang'][:2]
      if t['value'] == 'caption': new_lang += '-[CC]'
      if t['value'] == 'forced-subtitle': new_lang += '-[Forced]'
      t['new_lang'] = new_lang
      t['mod'] = track.replace('lang="{}"'.format(t['lang']), 'lang="{}"'.format(new_lang))
    if t['contentType'] == 'text':
      tracks['subs'].append(t)
    elif t['contentType'] == 'audio':
      tracks['audios'].append(t)
  return tracks
