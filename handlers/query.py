import requests
import json
import tornado
from dayu.db_conn import db_client
import os,json,traceback,re
from datetime import datetime
from dayu.util import convertDatetime, dingding
from config import auth
from urllib.parse import urlencode
import hmac
import base64

def generateSignature(msg, apiSecret):
    """OKEX签名V3"""
    mac = hmac.new(bytes(apiSecret, encoding='utf-8'), bytes(msg,encoding='utf-8'), digestmod='sha256')
    d= mac.digest()
    return base64.b64encode(d)

class rotate_query(object):
    def __init__(self):
        self.db_client = db_client()
        self.active_ac = {}
        self.contract_map = {}
        self.pos_dict={}
        self.cookies={"auth":auth}
        self.new_pos_dict={}
        self.mapping = {"1":"开多","2":"开空","3":"平多","4":"平空"}

    @tornado.gen.coroutine
    def prepare(self):
        res=requests.get("https://www.okex.com/api/futures/v3/instruments")
        for r in res.json():
            vert=f"{r['underlying_index']}-{r['alias'].replace('_','-')}"
            self.contract_map[str.upper(vert)]=r["instrument_id"]

        symbols=set()
        json_obj = self.db_client.query("strategy",{"server":{"$ne":"idle"}})
        for stg in json_obj:
            for sym in stg["symbolList"]:
                symbols.add(sym)
        for sym in list(symbols):
            s,vt_ac = sym.split(":")
            ss = self.active_ac.get(vt_ac,set())
            ss.add(s)
            self.active_ac.update({vt_ac:ss})

        json_obj = self.db_client.query("pos",{})
        for pos in json_obj:
            self.pos_dict.update({pos["name"]:[pos["long"],pos["short"]]})

        self.store()

    @tornado.gen.coroutine
    def store(self):
        json_obj =[]
        for vt_ac,symbols in self.active_ac.items():
            ac = vt_ac.split("_")[1]
            for symbol in list(symbols):
                for state in ["-1","2"]:
                    r = self.query(vt_ac, self.contract_map[symbol], state)
                    if r.get("result",False):
                        tmp=list(map(lambda x: dict(x,**{"account":vt_ac}),r["order_info"]))
                        result = list(map(lambda x: dict(x,**{"strategy":x["client_oid"].split("FUTU")[0]}),tmp))
                        json_obj += result

        json_obj=list(map(lambda x:dict(x, **{"datetime":convertDatetime(x["timestamp"])}),json_obj))
        success=[]
        for order in json_obj:
            if str(order["filled_qty"]) == "0":
                continue
            try:
                self.db_client.insert_one("orders",order)
                self.update_pos(order)
                success.append(order)
            except:
                pass
        print("find:",len(json_obj),"insert:",len(success))
        url = "http://localhost:9999/pos"
        body = urlencode({"pos":self.new_pos_dict})
        client = tornado.httpclient.AsyncHTTPClient()
        try:
            client.fetch(url,method='POST',body=body)
            self.new_pos_dict={}
        except Exception as e:
            print(e)

        if success:
            msg={}
            for od in success:
                stg=od["strategy"] if order["strategy"] else "None"
                ac = msg.get(stg,{})
                msg[stg]=ac
                txt = ac.get(od["account"],[])
                ding = f"> {od['instrument_id'].replace('-USD-','')},{self.mapping[od['type']]},{od['filled_qty']} @ {od['price_avg']}\n\n"
                txt.append(ding)
                msg[stg][od['account']]=txt
            ding = "DASHBOARD\n\n"
            for stg,detail in msg.items():
                ding+= f"### {stg}\n"
                for ac, txts in detail.items():
                    ding += f"### - {ac}:\n"
                    for txt in txts:
                        ding += txt
            ding += f"\n {datetime.now().strftime('%y%m%d %H:%M:%S')}"

            dingding("DASHBOARD",ding)

    def update_pos(self, order):
        strategy,direction,vol = order["strategy"],order["type"],float(order["filled_qty"])
        pos_long,pos_short = self.pos_dict.get(strategy,[0,0])

        if direction =="1":
            pos_long += vol
            self.new_pos_dict.update({f"long-{strategy}":pos_long})
        elif direction =="2":
            pos_short += vol
            self.new_pos_dict.update({f"short-{strategy}":pos_short})
        elif direction =="3":
            pos_long -= vol
            self.new_pos_dict.update({f"long-{strategy}":pos_long})
        elif direction =="4":
            pos_short -= vol
            self.new_pos_dict.update({f"short-{strategy}":pos_short})

        self.pos_dict[strategy] = [pos_long,pos_short]
        self.db_client.update_one("pos",{"name":strategy},{"name":strategy,"long":pos_long,"short":pos_short})
    

    def find_key(self,account_name):
        ex,ac = account_name.split("_")
        return self.db_client.query_one("account",{"name":ac})

    def query(self,account_name,symbol,state="",oid=""):
        setting = self.find_key(account_name)
        timestamp = f"{datetime.utcnow().isoformat()[:-3]}Z"
        if oid and not state:
            path = f'/api/futures/v3/orders/{symbol}/{oid}'
        elif state and not oid:
            path = f'/api/futures/v3/orders/{symbol}'
            params={"state":state,"instrument_id":symbol,"limit":100}
            path = f"{path}?{urlencode(params)}"
        else:
            return {}

        msg = f"{timestamp}GET{path}"
        signature = generateSignature(msg, setting["secretkey"])
        headers = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': setting["apikey"],
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': setting["passphrase"]
        }
        url = f"https://www.okex.com{path}"
        r = requests.get(url, headers = headers, timeout =10)
        return r.json()