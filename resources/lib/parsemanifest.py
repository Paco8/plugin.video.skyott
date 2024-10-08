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
  LOG('base_url: {}'.format(base_url))
  LOG('filename: {}'.format(filename_template))
  session = requests.Session()
  filename_template = filename_template.replace('$Number$', '{}')
  i = start_number
  res = []
  while True:
    if 'http' not in filename_template:
      url = base_url +'/' + filename_template.format(i)
    else:
      url = filename_template.format(i)
    LOG('Downloading {}'.format(url))
    response = session.get(url)
    if response.status_code != 200:
        break
    res.append(response.content.decode('utf-8'))
    i += 1
  return ''.join(res)

def parse_duration(duration):
  seconds = 0
  pattern = re.compile(r'PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?')
  match = pattern.match(duration)
  if match:
    time_params = {name: float(param) if param else 0 for name, param in match.groupdict().items()}
    seconds = (
        time_params['hours'] * 3600 +
        time_params['minutes'] * 60 +
        time_params['seconds']
    )
  return seconds

def extract_tracks(manifest):
  period_pattern = re.compile(r'<Period(.*?)</Period>', re.DOTALL)
  period_matches = re.findall(period_pattern, manifest)

  tracks = {'audios': [], 'subs': []}

  for period in period_matches:
      period_start_match = re.search(r'start="(.*?)"', period, re.DOTALL)
      period_start = period_start_match.group(1) if period_start_match else ''

      base_url_match = re.search(r'<BaseURL>(.*?)</BaseURL>\s*(?=<AdaptationSet)', period, re.DOTALL)
      base_url = base_url_match.group(1) if base_url_match else ''

      adaptation_set_pattern = re.compile(r'<AdaptationSet.*?</AdaptationSet>', re.DOTALL)
      matches = re.findall(adaptation_set_pattern, period)

      for track in matches:
        t = {'orig': track}
        for label in ['contentType', 'Label', 'lang', 'mimeType', 'value', 'codecs', 'startNumber', 'media']:
          m = re.search(r'{}="(.*?)"'.format(label), track, re.DOTALL)
          t[label] = m.group(1) if m else ''
        m = re.search(r'<BaseURL>(.*?)</BaseURL>', track, re.DOTALL)
        t['split'] = False
        t['filename'] = m.group(1) if m else ''
        if 'AdaptationSet' in track:
          if t['media'] and t['startNumber']:
            t['filename'] = t['media']
            t['start_number'] = t['startNumber']
            t['split'] = True
            del t['media']
            del t['startNumber']
        if t['contentType'] in ['text', 'audio']:
          new_lang = re.sub(r'-[A-Z]{2}', '', t['lang'])
          if t['value'] == 'caption': new_lang += '-[CC]'
          if t['value'] == 'forced-subtitle': new_lang += '-[Forced]'
          t['new_lang'] = new_lang
          t['mod'] = track.replace('lang="{}"'.format(t['lang']), 'lang="{}"'.format(new_lang))
        if t['contentType'] == 'text':
          t['period_start'] = parse_duration(period_start)
          t['base_url'] = base_url
          tracks['subs'].append(t)
        elif t['contentType'] == 'audio':
          tracks['audios'].append(t)
  return tracks
