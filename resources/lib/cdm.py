# encoding: utf-8
#
# SPDX-License-Identifier: LGPL-2.1-or-later

import requests
import json
import re
import base64
from .user_agent import chrome_user_agent
from .log import LOG

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
  headers = {'User-Agent': user_agent}
  data = {"license_url": license_url, "pssh": pssh}
  json_str = json.dumps(data)
  base64_bytes = base64.b64encode(json_str.encode('utf-8'))
  base64_str = base64_bytes.decode('utf-8')

  url = 'https://www.deliciasoft.com/sky.php?q=' + base64_str;

  response = session.get(url, headers=headers)
  #LOG(response.content)

  data = response.json()
  #LOG(data)

  return data.get('keys')

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
