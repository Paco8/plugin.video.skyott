# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

import requests
import json
import re
import base64
from .user_agent import chrome_user_agent
#from .log import LOG

user_agent = chrome_user_agent
session = requests.Session()

def get_pssh_from_manifest(url):
  headers = {'User-Agent': user_agent}
  response = session.get(url, headers=headers)
  content = response.content.decode('utf-8')
  pattern = r'<ContentProtection schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed">\s*<cenc:pssh.*?>(.*?)</cenc:pssh>'
  pssh = re.search(pattern, content, re.DOTALL)
  if pssh:
    return pssh.group(1)
  return None

def get_pssh_key(pssh, license_url):
  api_base_url = "https://cdm.drmtalks.com/"
  api_cdm_device = "01JCP8Y4W3PHM7DRQ5HGTME2CQ"
  headers = {'user-agent': user_agent, 'accept': '*/*'}
  session.headers.update(headers)

  open_session = session.get(api_base_url + api_cdm_device + '/open').json()
  #LOG(open_session.content)
  session_id = open_session["data"]["session_id"]

  challenge_api_data = {'session_id': session_id , 'init_data': None}
  challenge_api_data["init_data"] = pssh
  challenge_api_request = session.post(api_base_url + api_cdm_device + '/get_license_challenge/AUTOMATIC', json=challenge_api_data).json()
  #LOG(challenge_api_request)

  challenge_b64 = challenge_api_request['data']["challenge_b64"]
  #LOG(challenge_b64)
  challenge_raw = base64.b64decode(challenge_b64)

  license = session.post(license_url, data=challenge_raw)
  license.raise_for_status()
  #LOG(license.content)

  license_b64 = base64.b64encode(license.content).decode()
  #LOG('license_b64: {}'.format(license_b64))
  parse_license_data = {'session_id': session_id , 'license_message': license_b64}
  license_api_request = session.post(api_base_url + api_cdm_device + '/parse_license', json=parse_license_data).json()

  keys_api_data = {'session_id': session_id}
  keys_api_request = session.post(api_base_url + api_cdm_device + '/get_keys/CONTENT', json=keys_api_data).json()
  keys = keys_api_request['data']['keys']
  #LOG('keys: {}'.format(keys))
  res = []
  for key in keys:
    res.append('{}:{}'.format(key['key_id'], key['key']))

  close_session = session.get(api_base_url + api_cdm_device + '/close/' + session_id).text
  return ",".join(res)

def get_cdm_keys(manifest_url, license_url):
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
