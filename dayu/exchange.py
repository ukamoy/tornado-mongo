import os
import json
import requests
import hashlib
import hmac
import base64
from urllib.parse import urlencode
from datetime import datetime
import time

OKEX_BASE_URL = "https://www.okex.com"
BITMEX_BASE_URL = "https://testnet.bitmex.com/api/v1"
class BITMEX(object):
    def __init__(self, account):
        self.apikey = account["apikey"]
        self.secretkey = account["secretkey"]

    # public query -------------------------------
    @staticmethod
    def query_futures_price(instrument):
        r = requests.get(f'{BITMEX_BASE_URL}/instrument?symbol={instrument}', timeout = 10).json()
        return float(r[0]["lastPrice"])
    
    # sign -----------------------------------------
    def bitmex_sign(self, method, path, params = None):
        path = f"{path}?{urlencode(params)}" if method == "GET" and params else path
        data = urlencode(params) if method in ["POST", "DELETE"] else ""
        expires = int(time.time() + 30)
        msg = method + "/api/v1" + path + str(expires) + data
        signature = hmac.new(
            bytes(self.secretkey, encoding = 'utf8'),
            bytes(msg, encoding = 'utf8'),
            digestmod = hashlib.sha256).hexdigest()

        return f"{BITMEX_BASE_URL}{path}", {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "api-key": self.apikey,
            "api-expires": str(expires),
            "api-signature": signature }

    # private query -------------------------------
    def query_futures_orders(self, symbol, open_status = False):
        path = f'/order'
        params = {"symbol": symbol , "count": "100", "reverse": False}
        if open_status:
            params["filter"] = json.dumps({"open": True})
        url, headers = self.bitmex_sign("GET", path, params)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def query_futures_monoOrder(self, symbol, oid):
        path = f'/order'
        params = {"filter": json.dumps({"clOrdID": oid}), "symbol": symbol}
        url, headers = self.bitmex_sign("GET", path, params)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def query_futures_account(self, symbol):
        path = f'/user/wallet'
        params = {"currency": symbol}
        url, headers = self.bitmex_sign("GET", path, params)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def query_futures_position(self, symbol = ""):
        path = f'/position'
        params = {}
        if symbol:
            params["filter"] = json.dumps({"symbol": symbol})
        url, headers = self.bitmex_sign("GET", path, params)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def query_futures_monoPosition(self, symbol):
        path = f'/position/isolate'
        params = {"symbol": symbol}
        url, headers = self.bitmex_sign("GET", path, params)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def send_futures_order(self, oid, side, symbol, price, vol):
        path = f'/order'
        params = {
            "clOrdID": oid,
            "symbol": symbol,
            "side": side,
            "ordType": "Limit",
            "price": price,
            "orderQty": vol }
        url, headers = self.bitmex_sign("POST", path, params)
        r = requests.post(url, headers = headers, data = params, timeout = 10)
        return r.json()

    def cancel_futures_order(self, oid):
        path = f'/order'
        params = {"clOrdID": oid}
        url, headers = self.bitmex_sign("DELETE", path, params)
        r = requests.delete(url, headers = headers, data = params, timeout = 10)
        return r.json()


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
        contract_map = {}
        for contract in r:
            vert = f"{contract['underlying_index']}-{contract['alias'].replace('_','-')}"
            contract_map[str.upper(vert)] = contract["instrument_id"]
            contract_reverse = {v:k for k,v in contract_map.items()}
        return contract_map, contract_reverse

    @staticmethod
    def query_futures_price(instrument):
        url = f'{OKEX_BASE_URL}/api/futures/v3/instruments/{instrument}/ticker'
        r = requests.get(url, timeout = 10).json()
        return float(r["last"])

    @staticmethod
    def query_spot_price(instrument):
        url = f'{OKEX_BASE_URL}/api/spot/v3/instruments/{instrument}/ticker'
        r = requests.get(url, timeout = 10).json()
        return float(r["last"])

    # sign -----------------------------------------
    def okex_sign(self, method, path, params = None):
        body = json.dumps(params) if method == "POST" else ""
        path = f"{path}?{urlencode(params)}" if method == "GET" and params else path
        timestamp = f"{datetime.utcnow().isoformat()[:-3]}Z"
        msg = f"{timestamp}{method}{path}{body}"
        mac = hmac.new(
            bytes(self.secretkey, encoding = 'utf-8'), 
            bytes(msg, encoding = 'utf-8'), 
            digestmod = 'sha256').digest()

        return f"{OKEX_BASE_URL}{path}", {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.apikey,
            'OK-ACCESS-SIGN': base64.b64encode(mac),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase }

    # private query -------------------------------
    def query_futures_orders(self, symbol, state):
        path = f'/api/futures/v3/orders/{symbol}'
        params = {"state": state, "instrument_id": symbol, "limit": 100}
        url, headers = self.okex_sign("GET", path, params)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def query_futures_monoOrder(self, symbol, oid):
        path = f'/api/futures/v3/orders/{symbol}/{oid}'
        params = {"client_oid": oid, "instrument_id": symbol}
        url, headers = self.okex_sign("GET", path, params)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def query_futures_account(self, symbol):
        path = f'/api/futures/v3/accounts/{symbol}'
        url, headers = self.okex_sign("GET", path)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def query_position(self, symbol):
        path = f'/api/futures/v3/{symbol}/position'
        url, headers = self.okex_sign("GET", path)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def send_futures_order(self, oid, order_type, symbol, price, vol):
        path = f'/api/futures/v3/order'
        params = {"client_oid": oid,
            "instrument_id": symbol,
            "type": order_type,
            "price": price,
            "size": vol,
            "match_price": "0",
            "leverage": self.future_leverage}
        url, headers = self.okex_sign("POST", path, params)
        r = requests.post(url, headers = headers, data = params, timeout = 10)
        return r.json()

    def cancel_futures_order(self, symbol, oid):
        path = f'/api/futures/v3/cancel_order/{symbol}/{oid}'
        params = {"client_oid": oid, "instrument_id": symbol}
        url, headers = self.okex_sign("POST", path, params)
        r = requests.post(url, headers = headers, data = params, timeout = 10)
        return r.json()