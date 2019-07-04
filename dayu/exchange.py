
import os
import json
import requests
import hmac
import base64
from urllib.parse import urlencode
from datetime import datetime

OKEX_BASE_URL = "https://www.okex.com"

class OKEX(object):
    def __init__(self, account):
        self.apikey = account["apikey"]
        self.secretkey = account["secretkey"]
        self.passphrase = account["passphrase"]
        self.future_leverage = account["future_leverage"]

    # public query -------------------------------
    @staticmethod
    def query_futures_instruments():
        r = requests.get(f"{OKEX_BASE_URL}/api/futures/v3/instruments").json()
        contract_map={}
        for contract in r:
            vert = f"{contract['underlying_index']}-{contract['alias'].replace('_','-')}"
            contract_map[str.upper(vert)] = contract["instrument_id"]
            contract_reverse = {v:k for k,v in contract_map.items()}
        return contract_map, contract_reverse
    @staticmethod
    def query_futures_price(instrument):
        url = f'{OKEX_BASE_URL}/api/futures/v3/instruments/{instrument}/ticker'
        r = requests.get(url,timeout = 10).json()
        return float(r["last"])
    @staticmethod
    def query_spot_price(instrument):
        url = f'{OKEX_BASE_URL}/api/spot/v3/instruments/{instrument}/ticker'
        r = requests.get(url,timeout = 10).json()
        return float(r["last"])

    # sign -----------------------------------------
    def generateSignature(self, msg, apiSecret):
        mac = hmac.new(bytes(apiSecret, encoding='utf-8'), bytes(msg,encoding='utf-8'), digestmod='sha256')
        d = mac.digest()
        return base64.b64encode(d)

    def okex_sign(self, method, path, params = None):
        body = params if method == "POST" else ""
        timestamp = f"{datetime.utcnow().isoformat()[:-3]}Z"
        msg = f"{timestamp}{method}{path}{body}"
        signature = self.generateSignature(msg, self.secretkey)
        return {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.apikey,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase
        }

    # private query -------------------------------
    def query_futures_orders(self, symbol, state):
        path = f'/api/futures/v3/orders/{symbol}'
        params={"state":state, "instrument_id":symbol, "limit":100}
        path = f"{path}?{urlencode(params)}"
        headers = self.okex_sign("GET", path, params)
        url = f"{OKEX_BASE_URL}{path}"
        r = requests.get(url, headers = headers, timeout =10)
        return r.json()
    def query_futures_monoOrder(self, symbol, oid):
        path = f'/api/futures/v3/orders/{symbol}/{oid}'
        params={"client_oid":oid, "instrument_id":symbol}
        path = f"{path}?{urlencode(params)}"
        headers = self.okex_sign("GET", path, params)
        url = f"{OKEX_BASE_URL}{path}"
        r = requests.get(url, headers = headers, timeout =10)
        return r.json()

    def query_futures_account(self, symbol):
        path = f'/api/futures/v3/accounts/{symbol}'
        headers = self.okex_sign("GET", path)
        url = f"{OKEX_BASE_URL}{path}"
        r = requests.get(url, headers = headers, timeout =10)
        return r.json()

    def query_position(self, symbol):
        path = f'/api/futures/v3/{symbol}/position'
        headers = self.okex_sign("GET", path)
        url = f"{OKEX_BASE_URL}{path}"
        r = requests.get(url, headers = headers, timeout =10)
        return r.json()

    def send_futures_order(self, oid, order_type, symbol, price, vol):
        path = f'/api/futures/v3/order'
        params = {"client_oid": oid,
            "instrument_id":symbol,
            "type":order_type,
            "price":price,
            "size":vol,
            "match_price":"0",
            "leverage":self.future_leverage}
        params = json.dumps(params)
        headers = self.okex_sign("POST", path, params)
        url = f"{OKEX_BASE_URL}{path}"
        r = requests.post(url, headers = headers, data = params, timeout =10)
        return r.json()

    def cancel_futures_order(self, symbol, oid):
        path = f'/api/futures/v3/cancel_order/{symbol}/{oid}'
        params = {"client_oid":oid, "instrument_id":symbol}
        params = json.dumps(params)
        headers = self.okex_sign("POST", path, params)
        url = f"{OKEX_BASE_URL}{path}"
        r = requests.post(url, headers = headers, data = params, timeout =10)
        return r.json()