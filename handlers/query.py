import requests
import json
from dayu.db_conn import db_client
import os,json,traceback,re
from datetime import datetime
from dayu.queryorder import query
from dayu.util import convertDatetime
from config import auth

class rotate_query(object):
    def __init__(self):
        self.db_client = db_client()
        self.active_ac = {}
        self.contract_map = {}
        self.pos_dict={}
        self.header={"auth":auth}
        self.new_pos_dict={}
        
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

    def store(self):
        json_obj =[]
        for vt_ac,symbols in self.active_ac.items():
            ac = vt_ac.split("_")[1]
            for symbol in list(symbols):
                for state in ["-1","2"]:
                    r = query(ac, self.contract_map[symbol], state)
                    if r.get("result",False):
                        tmp=list(map(lambda x: dict(x,**{"account":vt_ac}),r["order_info"]))
                        result = list(map(lambda x: dict(x,**{"strategy":x["client_oid"].split("FUTU")[0]}),tmp))
                        json_obj += result

        json_obj=list(map(lambda x:dict(x, **{"datetime":convertDatetime(x["timestamp"])}),json_obj))
        i=0
        for order in json_obj:
            if str(order["filled_qty"]) == "0":
                continue
            try:
                self.db_client.insert_one("orders",order)
                self.update_pos(order)
                i+=1
            except:
                pass

        url=f"http://localhost:9999/pos?pos={json.dumps(self.new_pos_dict)}"
        try:
            requests.post(url,cookies=self.header,timeout=10)
            self.new_pos_dict={}
        except:
            pass
        print(f"{datetime.now().strftime('%y%m%d %H:%M:%S')}: find:{len(json_obj)}, insert:{i}")

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
