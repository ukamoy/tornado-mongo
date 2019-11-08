import os
import json
import re
import requests
import hashlib
import hmac
import base64
from urllib.parse import urlencode
from datetime import datetime
import time

OKEX_BASE_URL = "https://www.okex.com"
BITMEX_BASE_URL = "https://www.bitmex.com/api/v1"
HUOBI_SPOT_URL = "api.huobi.pro"
HUOBI_FUTURES_URL = "api.hbdm.com"
BINANCE_BASE_URL = "https://api.binance.com"

class BITMEX(object):
    def __init__(self, account):
        self.apikey = account["apikey"]
        self.secretkey = bytes(account["secretkey"], encoding = 'utf8')

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
        signature = hmac.new(self.secretkey,
            bytes(msg, encoding = 'utf8'),
            digestmod = hashlib.sha256).hexdigest()

        return f"{BITMEX_BASE_URL}{path}", {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "api-key": self.apikey,
            "api-expires": str(expires),
            "api-signature": signature }

    # private query -------------------------------
    def query_futures_orders(self, symbol, status = ""):
        path = f'/order'
        params = {"symbol": symbol , "count": "100", "reverse": False}
        if status:
            params["filter"] = json.dumps({"ordStatus": status})
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
        self.secretkey = bytes(account["secretkey"], encoding = 'utf-8')
        self.passphrase = account["passphrase"]
        self.future_leverage = account["future_leverage"]

    # public query -------------------------------
    @staticmethod
    def query_futures_instruments(): 
        r = requests.get(f"{OKEX_BASE_URL}/api/futures/v3/instruments").json()
        contract_map = {}
        for contract in r:
            if contract["quote_currency"] == "USDT":
                continue
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
        print(msg)
        mac = hmac.new(self.secretkey, 
            bytes(msg, encoding = 'utf-8'), 
            digestmod = 'sha256').digest()

        return f"{OKEX_BASE_URL}{path}", {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.apikey,
            'OK-ACCESS-SIGN': base64.b64encode(mac),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase }
    def query_wallet(self):
        path = "/api/futures/v3/accounts/btc"
        url, headers = self.okex_sign("GET", path)
        r = requests.get(url, headers = headers, timeout = 10)
        print(r.json())

    # private query -------------------------------
    def query_futures_orders(self, symbol, state):
        path = f'/api/futures/v3/orders/{symbol}'
        state_map = {"New": "0", "Filled": "2", "Canceled": "-1", "Partially filled": "1", "Rejected": "-2"}
        params = {"state": state_map.get(state, state), "instrument_id": symbol, "limit": 100}
        # params["after"] = "3712845163926528"
        # params["before"] = "3712845163926529"

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
    def query_futures_leverage(self,symbol):
        path= f'/api/futures/v3/accounts/{symbol}/leverage'
        url, headers = self.okex_sign("GET", path)
        r = requests.get(url, headers = headers, timeout = 10)
        return r.json()

    def set_futures_leverage(self,symbol,value):
        path= f'/api/futures/v3/accounts/{str.lower(symbol)}/leverage'
        params = {"leverage": value}
        url, headers = self.okex_sign("POST", path, params)
        r = requests.post(url, headers = headers, data = json.dumps(params), timeout = 10)
        return r.json()
        
    def set_account_type(self,symbol):
        path = f'/api/futures/v3/accounts/margin_mode'
        params = {"margin_mode": "crossed","currency":str.lower(symbol)}
        url, headers = self.okex_sign("POST", path,params)
        r = requests.post(url, headers = headers, data = json.dumps(params), timeout = 10)
        return r.json()

    def query_futures_position(self, symbol):
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
        r = requests.post(url, headers = headers, data = json.dumps(params), timeout = 10)
        return r.json()

    def cancel_futures_order(self, symbol, oid):
        path = f'/api/futures/v3/cancel_order/{symbol}/{oid}'
        params = {"client_oid": oid, "instrument_id": symbol}
        url, headers = self.okex_sign("POST", path, params)
        r = requests.post(url, headers = headers, data = json.dumps(params), timeout = 10)
        return r.json()

class HUOBI(object):
    def __init__(self, account):
        self.apikey = account["apikey"]
        self.secretkey = account["secretkey"].encode(encoding = 'UTF8')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML,like Gecko) Chrome/39.0.2171.71 Safari/537.36',
            'Content-Type': 'application/json'}

    # public query -------------------------------
    @staticmethod
    def query_spot_symbols():
        r = requests.get(f'https://{HUOBI_SPOT_URL}/v1/common/symbols', timeout = 10).json()
        symbol_map = {}
        for symbol_info in r.get("data",[]):
            symbol_map.update({symbol_info["symbol"]:symbol_info["base-currency"]})
        return symbol_map
    @staticmethod
    def query_futures_instruments():
        r = requests.get(f'https://{HUOBI_FUTURES_URL}/api/v1/contract_contract_info', timeout = 10).json()
        contract_map = {}
        for contract in r.get("data",[]):
            vert = f"{contract['symbol']}-{contract['contract_type'].replace('_','-')}"
            contract_map[str.upper(vert)] = contract["contract_code"]
            contract_reverse = {v:k for k,v in contract_map.items()}
        return contract_map, contract_reverse

    # sign -----------------------------------------
    def huobi_sign(self, method, host, path, params = {}):
        sortedParams = [
                ("AccessKeyId", self.apikey),
                ("SignatureMethod", "HmacSHA256"),
                ("SignatureVersion", "2"),
                ("Timestamp", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
            ]
        if params:
            sortedParams.extend(list(params.items()))
            sortedParams = list(sorted(sortedParams))

        payload = [method, host, path, urlencode(sortedParams)]
        payload = "\n".join(payload)
        
        digest = hmac.new(self.secretkey,
            payload.encode(encoding = "UTF8"),
            digestmod = hashlib.sha256).digest()
        signature = base64.b64encode(digest)

        new_param = dict(sortedParams)
        new_param["Signature"] = signature.decode("UTF8")
        return f"https://{host}{path}?{urlencode(new_param)}", new_param

    # private -----------------------------------------
    def query_spot_account(self, symbol = ""):
        path = f'/v1/account/accounts'
        url, params = self.huobi_sign("GET", HUOBI_SPOT_URL, path)
        r = requests.get(url, headers = self.headers, timeout = 10)
        account = {}
        for ac_id in r.json().get("data",[]):
            path = f"/v1/account/accounts/{ac_id['id']}/balance"
            url, params = self.huobi_sign("GET", HUOBI_SPOT_URL, path)
            r = requests.get(url, headers = self.headers, timeout = 10)
            account_info = {}
            print(r.content)
            for ac in r.json().get("data",{}).get("list",[]):
                if ac.get("type","")=="trade":
                    account_info[ac["currency"]] = ac["balance"]
            account[ac_id["id"]] = account_info
        return account

    def query_futures_account(self, symbol = ""):
        path = f'/api/v1/contract_account_info'
        params =  {"symbol": symbol} if symbol else {}
        url, params = self.huobi_sign("POST", HUOBI_FUTURES_URL, path, params)
        r = requests.post(url, headers = self.headers, timeout = 10)
        account = {}
        for ac in r.json().get("data",[]):
            account.update({ac["symbol"]:ac["margin_available"]})
        return account

    def query_spot_orders(self, symbol, state):
        path = f'/v1/order/orders'
        params = {"symbol":str.lower(symbol.replace("-","")),"states":state}
        url, params = self.huobi_sign("GET", HUOBI_SPOT_URL, path, params)
        r = requests.get(url, headers = self.headers, timeout = 10)
        return r.json().get("data",[])

    def query_spot_monoOrder(self, oid, symbol = ""):
        path = f'/v1/order/orders/getClientOrder'
        params = {"clientOrderId":oid}
        url, params = self.huobi_sign("GET", HUOBI_SPOT_URL, path, params)
        r = requests.get(url, headers = self.headers, timeout = 10)
        return r.json().get("data",[])

    def query_futures_orders(self, symbol, state):
        path = f'/api/v1/contract_hisorders'
        state_map = {"New": 3, "Filled": 6, "Canceled": 5, "Rejected":999}
        params = {"symbol":symbol.split("-")[0], "status": state_map[state],
                "trade_type":0, "type":1,"create_date":90, "page_size":50}
        url, params = self.huobi_sign("POST", HUOBI_FUTURES_URL, path, params)
        r = requests.post(url, headers = self.headers, timeout = 10)
        return r.json().get("data",[])

    def query_futures_monoOrder(self, oid, symbol):
        path = f'/api/v1/contract_order_info'
        params = {"symbol":symbol.split("-")[0], "client_order_id": oid}
        url, params = self.huobi_sign("POST", HUOBI_FUTURES_URL, path, params)
        r = requests.post(url, headers = self.headers, timeout = 10)
        print(r.json())
        return r.json().get("data",[])

    def send_spot_order(self, oid, order_type, symbol, price, qty):
        pass
    def send_futures_order(self, oid, order_type, symbol, price, qty):
        pass
        
    def cancel_spot_order(self, oid, order_type, symbol, price, qty):
        pass
    def cancel_futures_order(self, oid, order_type, symbol, price, qty):
        pass

class BINANCE(object):
    def __init__(self, account):
        self.apikey = account["apikey"]
        self.secretkey = account["secretkey"].encode()
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-MBX-APIKEY": self.apikey
        }
        self.time_offset = self.query_time()
        self.symbol_map = self.query_spot_symbols()

    def query_time(self):
        r = requests.get(f'{BINANCE_BASE_URL}/api/v1/time', timeout = 10).json()
        local_time = int(time.time() * 1000)
        server_time = int(r.get("serverTime", 0))
        return local_time - server_time

    # public query -------------------------------
    @staticmethod
    def query_spot_symbols():
        r = requests.get(f'{BINANCE_BASE_URL}/api/v1/exchangeInfo', timeout = 10).json()
        symbol_map = {}
        for symbol_info in r.get("symbols",[]):
            symbol_map.update({symbol_info["symbol"]:symbol_info["baseAsset"]})
        return symbol_map

    @staticmethod
    def query_spot_price(symbol):
        params =  {"symbol":symbol.replace("-","")}
        r = requests.get(f'{BINANCE_BASE_URL}/api/v1/ticker/24hr', params = params, timeout = 10).json()
        return r.get("lastPrice", 0)

    @staticmethod
    def query_futures_instruments():
        r = requests.get(f'{BINANCE_BASE_URL}/api/v1/BINANCE_BASE_URL', timeout = 10).json()
        contract_map = {}
        for contract in r.get("data",[]):
            vert = f"{contract['symbol']}-{contract['contract_type'].replace('_','-')}"
            contract_map[str.upper(vert)] = contract["contract_code"]
            contract_reverse = {v:k for k,v in contract_map.items()}
        return contract_map, contract_reverse

    # sign -----------------------------------------
    def binance_sign(self, method, path, params = {}):
        timestamp = int(time.time() * 1000)
        if self.time_offset > 0:
            timestamp -= abs(self.time_offset)
        elif self.time_offset < 0:
            timestamp += abs(self.time_offset)
        params["timestamp"] = timestamp

        msg = urlencode(sorted(params.items()))
        signature = hmac.new(self.secretkey,
            msg.encode("utf-8"), hashlib.sha256).hexdigest()

        msg += f"&signature={signature}"
        path = path + "?" + msg
        return f"{BINANCE_BASE_URL}{path}"

    # private -----------------------------------------
    def query_spot_account(self, symbol):
        path = f'/api/v3/account'
        url = self.binance_sign("GET", path)
        return requests.get(url, headers = self.headers, timeout = 10).json()

    def query_spot_orders(self, symbol, state):
        if state == "filled":
            path = "/api/v3/myTrades"
        elif state == "active":
            path = "/api/v3/openOrders"
        else:
            path = "/api/v3/allOrders"

        params = {"symbol": symbol.replace("-","")}
        url = self.binance_sign("GET", path, params)
        return requests.get(url, headers = self.headers, timeout =10).json()

    def query_spot_monoOrder(self, symbol, oid):
        pass
    def send_spot_order(self, oid, order_type, price, qty):
        pass
    def cancel_spot_order(self, oid):
        pass

def _split_url(url):
    result = re.match("\w+://([^/]*)(.*)",url)
    print(result.group(2))