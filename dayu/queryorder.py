import requests,json
from urllib.parse import urlencode
from datetime import datetime
import hmac
import base64

import okex.account_api as account
import okex.futures_api as future
import okex.lever_api as lever
import okex.spot_api as spot
import okex.swap_api as swap

def find_key(account_name):
    key_path = f"/home/dayu/Documents/APIKEY_READ_ONLY/OKEX_{account_name}_connect.json"
    with open(key_path) as f:
        setting = json.load(f)
    return setting
def generateSignature(msg, apiSecret):
    """OKEX签名V3"""
    mac = hmac.new(bytes(apiSecret, encoding='utf-8'), bytes(msg,encoding='utf-8'), digestmod='sha256')
    d= mac.digest()
    return base64.b64encode(d)
def query(account_name,symbol,state="",oid=""):
    setting = find_key(account_name)
    timestamp = f"{datetime.utcnow().isoformat()[:-3]}Z"
    if oid and not state:
        path = f'/api/futures/v3/orders/{symbol}/{oid}'
    elif state and not oid:
        path = f'/api/futures/v3/orders/{symbol}'
        params={"state":7,"instrument_id":symbol,"limit":100}
        path = path+"?"+urlencode(params)
    else:
        return {}

    msg = f"{timestamp}GET{path}"
    signature = generateSignature(msg, setting["apiSecret"])
    headers = {
        'Content-Type': 'application/json',
        'OK-ACCESS-KEY': setting["apiKey"],
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': setting["passphrase"]
    }
    url = f"https://www.okex.com{path}"
    r = requests.get(url, headers = headers, timeout =10)
    return r.json()