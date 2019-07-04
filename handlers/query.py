import requests
import json
import tornado
from dayu.db_conn import db_client
import os,json,traceback,re
from datetime import datetime
from dayu.util import convertDatetime, dingding, get_server
from dayu.exchange import OKEX
from urllib.parse import urlencode
import hmac
import base64
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import pandas as pd
from config import working_path

IMAGE = "daocloud.io/xingetouzi/vnpy-fxdayu:v1.1.20"

class rotate_query(object):
    executor = ThreadPoolExecutor(10)
    def __init__(self):
        self.db_client = db_client()
        self.pos_dict={}
        self.new_pos_dict={}
        self.key_chain = {}
        self.mapping = {"1":"开多","2":"开空","3":"平多","4":"平空"}

    @tornado.gen.coroutine
    def prepare(self):
        symbols = set()
        coins = set()
        active_ac={}
        json_obj = self.db_client.query("strategy",{"server":{"$ne":"idle"}})

        for stg in json_obj:
            for sym,pos in stg["tradePos"].items():
                symbols.add(sym)
                self.pos_dict.update({f"{stg['alias']}-{sym}":pos})

        for sym in list(symbols):
            s,vt_ac = sym.split(":")
            ss = active_ac.get(vt_ac, set())
            ss.add(s)
            coins.add(s)
            active_ac.update({vt_ac:ss})
        coins = list(set(map(lambda x: x.split("-")[0], list(coins))))
        keys = list(map(lambda x: x.split("_")[1], list(active_ac.keys())))
        keys = self.db_client.query("account",{"name":{"$in":keys}})
        for key in keys:
            self.key_chain.update({f"OKEX_{key['name']}":key})
        self.okex_orders(active_ac)
        self.okex_accounts(active_ac, coins)
        self.auto_launch()
        #self.test()

    # def test(self):
    #     for i in range(10):
    #         url = "http://localhost:9999/test"
    #         body=urlencode({"test":i})
    #         client = tornado.httpclient.AsyncHTTPClient()
    #         client.fetch(url,method='POST',body=body)
    # @run_on_executor
    # def test2(self,server_name,stg_name,task_id):
    #     sleep(8)
    #     print("888888")

    @tornado.gen.coroutine
    def auto_launch(self):
        not_run = self.db_client.query("tasks",{"status":0,"server":"idle"})
        if not_run:
            stg_list = list(map(lambda x: x["strategy"],not_run))
            dingding("INSTANCE",f"ATTEMPT AUTO-LAUNCH: {stg_list}")
            servers = self.db_client.query("server",{"type":"trading"})
            servers_list = list(map(lambda x: x["server_name"],servers))
            running_instance = self.db_client.query("tasks",{"status":1})
            running_serv= list(map(lambda x: x["server"],running_instance))

            for instance in not_run:
                serv=None
                for serv_r in list(set(sorted(running_serv))):
                    print("find existing:",instance["strategy"],serv_r,running_serv.count(serv_r))
                    if running_serv.count(serv_r)<7:
                        serv=serv_r
                        running_serv.append(serv)
                        break
                if not serv:
                    f = sorted(list(set(servers_list)^set(running_serv)))
                    print("NEW servers:",f)
                    if f:
                        serv=f[0]
                        running_serv.append(serv)
                    else:
                        dingding("INSTANCE","Auto-launch failed, NEED NEW SERVER")
                        break
                #yield self.test2(serv,instance["strategy"],instance["task_id"])
                yield self.launch_process(serv,instance["strategy"],instance["task_id"])
 
    @run_on_executor
    def launch_process(self, server_name,stg_name,task_id):
        server = get_server(server_name)
        if server:
            container = server.get(stg_name)
            if not container:
                r = server.create(
                    IMAGE, # 镜像名
                    stg_name, # 策略名
                    f"{working_path}/{task_id}/{stg_name}"
                )
                print("create container:",r)
            
            status = server.start(stg_name)
            if status == "running":
                now = int(datetime.now().timestamp()*1000)
                self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"server":server_name,"status":1})
                self.db_client.update_one("strategy",{"name":stg_name},{"server":server_name})
                self.db_client.insert_one("operation",{"name":stg_name,"op":1,"timestamp":now})
    
    @tornado.gen.coroutine
    def okex_accounts(self, active_ac, coins):
        today = datetime.today().strftime("%Y%m%d")
        for coin in coins:
            r = OKEX.query_spot_price(f"{coin}-USDT")
            self.db_client.update_one("coin_value",{"date":today,"coin":coin},{"date":today,"coin":coin,"value":r})

        for vt_ac,symbols in active_ac.items():
            d={}
            for symbol in list(symbols):
                gateway = OKEX(self.key_chain[vt_ac])
                r = gateway.query_futures_account(symbol[:3])
                d.update({symbol[:3]:float(r["equity"])})
            self.db_client.update_one("account_value",{"date":today,"account":vt_ac},{"date":today,"account":vt_ac,"FUTURE":d})

    @tornado.gen.coroutine
    def okex_orders(self, active_ac):
        order_list =[]
        open_orders = []
        contract_map, contract_reverse = OKEX.query_futures_instruments()
        for vt_ac,symbols in active_ac.items():
            gateway = OKEX(self.key_chain[vt_ac])
            for symbol in list(symbols):
                for state in ["-1","2"]:
                    r = gateway.query_futures_orders(contract_map[symbol],state)
                    if r.get("result",False):
                        result = list(map(lambda x: dict(x,**{"account":vt_ac}),r["order_info"]))
                        result = list(map(lambda x: dict(x,**{"strategy":x["client_oid"].split("FUTU")[0]}),result))
                        result = list(map(lambda x: dict(x,**{"instrument_id":symbol}), result))
                        order_list += result
                r = gateway.query_futures_orders(contract_map[symbol], "6")
                if r.get("result",False):
                    result = list(map(lambda x: dict(x,**{"account":vt_ac}),r["order_info"]))
                    result = list(map(lambda x: dict(x,**{"strategy":x["client_oid"].split("FUTU")[0]}),result))
                    result = list(map(lambda x: dict(x,**{"instrument_id":symbol}), result))
                    open_orders += result

        if order_list:
            order_list=list(map(lambda x:dict(x, **{"datetime":convertDatetime(x["timestamp"])}),order_list))
        success=[]
        for order in order_list:
            if str(order["filled_qty"]) == "0":
                continue
            try:
                self.db_client.insert_one("orders",order)
                self.update_pos(order)
                success.append(order)
            except:
                pass
        open_order_map ={}
        if open_orders:
            for order in open_orders:
                key = f"open-{order['strategy']}-{order['instrument_id']}:{order['account']}"
                size = open_order_map.get(key, 0)
                open_order_map.update({key:size + int(order["size"])})
            for k, v in open_order_map.items():
                print("openooooooooooooooooooooooo",k)
                alias = k.split("-")[1]
                if alias:
                    self.db_client.update_one(
                        "strategy",
                        {"alias",alias},{"open_order":{k.replace(f"open-{alias}-",""):v}}
                    )
                    
        print("find:",len(order_list),"insert:",len(success),"order pending:",len(open_orders))
        url = "http://localhost:9999/pos"
        self.new_pos_dict.update(open_order_map)
        body = urlencode(self.new_pos_dict)
        client = tornado.httpclient.AsyncHTTPClient()
        try:
            client.fetch(url,method='POST',body=body)
            self.new_pos_dict={}
        except Exception as e:
            print("client.fetch failed. reason:",e)

        if success:
            msg={}
            for od in success:
                stg=od["strategy"] if order["strategy"] else "None"
                ac = msg.get(stg,{})
                msg[stg]=ac
                txt = ac.get(od["account"],[])
                ding = f"> {od['instrument_id']}, {self.mapping[od['type']]}, {od['filled_qty']} @ {od['price_avg']}\n\n"
                txt.append(ding)
                msg[stg][od['account']]=txt
            ding = ""
            for stg,detail in msg.items():
                ding+= f"### {stg}\n"
                for ac, txts in detail.items():
                    ding += f"#### - {ac}:\n"
                    for txt in txts:
                        ding += txt
            ding += f"\n {datetime.now().strftime('%y%m%d %H:%M:%S')}"

            dingding("DASHBOARD",ding)

    def update_pos(self, order):
        strategy,sym,ac = order["strategy"],order["instrument_id"],order["account"]
        direction,vol = order["type"],int(order["filled_qty"])
        vt_ac = f"{sym}:{ac}"
        key = f"{strategy}-{vt_ac}"
        pos_long,pos_short = self.pos_dict.get(key,[0,0])

        if direction =="1":
            pos_long += vol
            self.new_pos_dict.update({f"long-{key}":pos_long})
        elif direction =="2":
            pos_short += vol
            self.new_pos_dict.update({f"short-{key}":pos_short})
        elif direction =="3":
            pos_long -= vol
            self.new_pos_dict.update({f"long-{key}":pos_long})
        elif direction =="4":
            pos_short -= vol
            self.new_pos_dict.update({f"short-{key}":pos_short})

        self.pos_dict[key] = [pos_long,pos_short]
        if strategy:
            self.db_client.update_one(
                "strategy",
                {"alias":strategy},
                {"tradePos":{vt_ac:[pos_long,pos_short]}})

class position_span(object):
    def __init__(self, instrument):
        self.long_price = 0
        self.long_qty = 0
        self.short_price = 0
        self.short_qty = 0

        self.profit_loss = 0
        self.fee = 0
        self.contract_value = 0
        self.trade_count = 0
        self.winning_count = 0
        self.winning_pnl = 0
        self.position_profit = 0
        self.instrument = instrument
        self.missing_open = []
        self.pnl_list = []
        self.qty_list = []
        

    def add_up_buy_orders(self, price, qty):
        pre_price = self.long_price * self.long_qty
        self.long_qty += qty
        self.long_price = (pre_price + (price * qty)) / self.long_qty
    
    def add_up_short_orders(self, price, qty):
        pre_price = self.short_price * self.short_qty
        self.short_qty += qty
        self.short_price = (pre_price + (price * qty)) / self.short_qty

    def sell_long_holding(self, price, qty):
        #  平多盈亏： (合约面值 / 结算基准价 – 合约面值 / 平均平仓价格) * 平仓数量
        self.trade_count += 1
        pnl = (( self.contract_value / self.long_price - self.contract_value / price ) * qty)
        self.profit_loss += pnl
        self.long_qty -= qty
        if pnl >0:
            self.winning_count+=1
            self.winning_pnl += pnl
        if not self.long_qty:
            self.long_price = 0

    def cover_short_holding(self, price, qty):
        #  平空盈亏： (合约面值 / 平均平仓价格 – 合约面值 / 结算基准价) * 平仓数量 
        self.trade_count += 1
        pnl = (( self.contract_value / price - self.contract_value / self.short_price ) * qty)
        self.profit_loss += pnl
        self.short_qty -= qty
        if pnl >0:
            self.winning_count+=1
            self.winning_pnl += pnl
        if not self.short_qty:
            self.short_price = 0

    def calculate_position_profit(self, price):
        # 持仓盈亏
        if self.long_qty:
            self.position_profit += ( ( self.contract_value / self.long_price - self.contract_value / price ) * self.long_qty )
        if self.short_qty:
            self.position_profit += ( ( self.contract_value / price - self.contract_value / self.short_price ) * self.short_qty )


# 订单处理
def process_orders(order_data, pos_dict):
    for idx, order in order_data.iterrows():
        order_price = float(order['price_avg'])
        order_qty = int(order['filled_qty'])

        pos_dict.fee += float(order['fee'])
        pos_dict.contract_value = float(order["contract_val"])
        
        if str(order['type']) == "1":
            pos_dict.add_up_buy_orders(order_price, order_qty)
        
        elif str(order['type']) == "2":
            pos_dict.add_up_short_orders(order_price, order_qty)
        
        elif str(order['type']) == "3":
            if pos_dict.long_qty < order_qty:
                pos_dict.missing_open.append(f"{order['datetime']}, hold_long:{pos_dict.long_qty} vs. sell_qty:{order_qty}")
                continue
            pos_dict.sell_long_holding(order_price, order_qty)
        
        elif str(order['type']) == "4":
            if pos_dict.short_qty < order_qty:
                pos_dict.missing_open.append(f"{order['datetime']}, hold_short:{pos_dict.short_qty} vs. cover_qty:{order_qty}")
                continue
            pos_dict.cover_short_holding(order_price, order_qty)
        t= int(order['datetime'].timestamp()*1000)
        pos_dict.pnl_list.append([t,pos_dict.profit_loss])
        pos_dict.qty_list.append([t,order_qty])

def get_chart(strategy, json_obj, hist):
    df = pd.DataFrame(json_obj)
    result={}
    statistics = {}

    overview = {}
    winning_count = 0
    winning_pnl = 0
    total_count = 0
    total_pnl = 0
    
    if df.size > 0:
        del df["_id"]
        data = df.sort_values(by = "datetime", ascending = True)
        data["vtSymbol"] = data["instrument_id"]+":"+data["account"]
        instruments = list(set(data["vtSymbol"]))
        contract_map, contract_reverse = OKEX.query_futures_instruments()
        for instrument in instruments:
            per_coin_data = data[data["vtSymbol"] == instrument]
            pos_dict = position_span(instrument)
            process_orders(per_coin_data, pos_dict)
            symbol = contract_map[instrument.split(":")[0]]
            pos_dict.calculate_position_profit(OKEX.query_futures_price(symbol))

            # 缓存策略统计
            result[instrument] = pos_dict

        for instrument, position in result.items():
            statistics[instrument] = {
                "symbol" : instrument,
                "trade_count" : position.trade_count,
                "profit_loss" : position.profit_loss,
                "fee" : position.fee,
                "position_profit" : position.position_profit,
                "net_profit" : position.profit_loss + position.fee + position.position_profit,
                "holding_long" : position.long_qty,
                "holding_short" : position.short_qty,
                "missing_open" : position.missing_open,
                "pnl": position.pnl_list,
                "qty":position.qty_list
            }
            winning_count+=position.winning_count
            winning_pnl+=position.winning_pnl
            total_count+=position.trade_count
            total_pnl+=position.profit_loss

    avg_win = 0
    avg_loss = 0
    pnl_ratio = 0
    winning_rate = 0
    if winning_count:
        avg_win = winning_pnl / winning_count
    if total_count-winning_count:
        avg_loss = (total_pnl-winning_pnl) / (total_count-winning_count)
    if avg_loss:
        pnl_ratio = avg_win / avg_loss * -1
    if total_count:
        winning_rate = winning_count / total_count
    overview={
        "total_count" : total_count,
        "winning_rate" : f"{winning_rate:0.2%}",
        "pnl_ratio" : f"{pnl_ratio:0.2f}",
        "running_hist":list(map(lambda x:[x["timestamp"],x["op"]],hist)),
        "detail":statistics
    }
    return overview