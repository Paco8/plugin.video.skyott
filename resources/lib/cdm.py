# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

import requests
import json
import re
import base64
import os

from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH

from .user_agent import chrome_user_agent
from .log import LOG

user_agent = chrome_user_agent
session = requests.Session()

try:
  from .addon import profile_dir
  device_file = os.path.join(profile_dir, 'device.wvd')
except:
  device_file = './device.wvd'
LOG('Device filename: {}'.format(device_file))

def installed_device():
  return os.path.exists(device_file)

def get_pssh_from_manifest(url):
  headers = {'User-Agent': user_agent}
  response = session.get(url, headers=headers)
  content = response.content.decode('utf-8')
  pattern = r'<ContentProtection schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed">\s*<cenc:pssh.*?>(.*?)</cenc:pssh>'
  pssh = re.search(pattern, content, re.DOTALL)
  if pssh:
    return pssh.group(1)
  return None

def get_pssh_key(pssh_text, license_url):
  pssh = PSSH(pssh_text)
  device = Device.load(device_file)
  cdm = Cdm.from_device(device)
  session_id = cdm.open()
  challenge = cdm.get_license_challenge(session_id, pssh)
  #print(challenge)
  #print('challenge: {}'.format(encode_base64(challenge)))

  headers = {
    'User-Agent': user_agent,
    'Accept': '*/*',
  }

  license = requests.post(license_url, data=challenge, headers=headers)
  license.raise_for_status()
  #print(license.content)

  cdm.parse_license(session_id, license.content)

  # Get keys
  keys = []
  cdm_keys = cdm.get_keys(session_id)
  for key in cdm_keys:
    if key.type == 'CONTENT':
      keys.append('{}:{}'.format(key.kid.hex, key.key.hex()))
    #print(f"[{key.type}] {key.kid.hex}:{key.key.hex()}")

  cdm.close(session_id)
  return ",".join(keys)

def get_cdm_keys(manifest_url, license_url):
  if not installed_device():
    LOG('Error: {} not found'.format(device_file))
    return {'error': 'device.wvd not found'}

  pssh = get_pssh_from_manifest(manifest_url)
  #LOG('pssh: {}'.format(pssh))
  d = {}
  if pssh:
    try:
      key = get_pssh_key(pssh, license_url)
      d['key'] = key
    except Exception as e:
      d['error'] = str(e)
  else:
    d['error'] = 'pssh not found'
  return d
