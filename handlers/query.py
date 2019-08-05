import requests
import json
import tornado
import os, traceback, re
from datetime import datetime
from time import sleep

from dayu.util import convertDatetime, dingding, get_server
from dayu.db_conn import db_client
from dayu.exchange import OKEX, BITMEX
from urllib.parse import urlencode
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from config import working_path

#IMAGE = "daocloud.io/xingetouzi/vnpy-fxdayu:v1.1.20"
IMAGE = "daocloud.io/xingetouzi/vnpy-fxdayu:v1.1.21-20190729"
class rotate_query(object):
    executor = ThreadPoolExecutor(15)
    def __init__(self):
        self.db_client = db_client()
        self.pos_dict = {}
        self.new_pos_dict = {}
        self.key_chain = {}
        self.open_order_cache = {}
        self.coin_values = {}
        self.mapping = {"1":"开多","2":"开空","3":"平多","4":"平空"}
        self.prepare()

    @tornado.gen.coroutine
    def prepare(self):
        self.auto_launch()

        active_ac = yield self.key_maker()
        filled_orders = []
        for ex, ac in active_ac.items():
            coins = list(set(sum(list(ac.values()),[])))
                
            if ex=="OKEX" and ac:
                filled_orders += yield self.okex_orders(ac, coins)
                self.okex_accounts(ac, coins)

            elif ex == "BITMEX" and ac:
                filled_orders += yield self.bitmex_orders(ac, coins)
                self.bitmex_accounts(ac, coins)
        
        if filled_orders:
            success_order = yield self.process_filled_orders(filled_orders)
        self.get_position_profit(self.coin_values)
        self.send_pos()
        self.dingding_pos(success_order)

    @run_on_executor
    def key_maker(self):
        json_obj = self.db_client.query("strategy", {"server": {"$ne":"idle"}})
        
        symbols = set()
        for stg in json_obj:
            for sym, pos in stg["tradePos"].items():
                symbols.add(sym)
                self.pos_dict.update({f"{stg['alias']}-{sym}":pos})
        
        active_ac = {"OKEX": {}, "BITMEX": {}}
        for symbol in list(symbols):
            sym, vt_ac = symbol.split(":")
            ex, ac = vt_ac.split("_")
            ss = active_ac[ex].get(vt_ac, [])
            ss.append(sym)
            active_ac[ex].update({vt_ac: list(set(ss))})
        
        keys = []
        for ex, ac in active_ac.items():
            k = list(map(lambda x: x.split("_")[1], list(ac.keys())))
            keys += self.db_client.query("account", {"exchange":ex, "name":{"$in":k}})
            
        for key in keys:
            self.key_chain.update({f"{key['exchange']}_{key['name']}": key})
        return active_ac

    @run_on_executor
    def test(self):
        for i in range(10):
            url = "http://localhost:9999/test"
            body = urlencode({"test": i})
            client = tornado.httpclient.AsyncHTTPClient()
            client.fetch(url, method = 'POST', body = body)

    @tornado.gen.coroutine
    def auto_launch(self):
        not_run = self.db_client.query("tasks", {"status": 0, "server": "idle"})
        if not_run:
            stg_list = list(map(lambda x: x["strategy"], not_run))
            dingding("INSTANCE", f"> ATTEMPT AUTO-LAUNCH: {stg_list}")
            servers = self.db_client.query("server", {"type": "trading"})
            servers_list = list(map(lambda x: x["server_name"], servers))
            running_instance = self.db_client.query("tasks", {"status": 1})
            running_serv= list(map(lambda x: x["server"], running_instance))
            msg = "### AUTO-LAUNCHER\n\n"
            for instance in not_run:
                serv=None
                for serv_r in list(set(sorted(running_serv))):
                    print("find existing:", instance["strategy"], serv_r, running_serv.count(serv_r))
                    if running_serv.count(serv_r) < 7:
                        serv = serv_r
                        running_serv.append(serv)
                        break
                if not serv:
                    f = sorted(list(set(servers_list)^set(running_serv)))
                    print("NEW servers:", f)
                    if f:
                        serv=f[0]
                        running_serv.append(serv)
                    else:
                        dingding("INSTANCE", "> Auto-launch failed, NEED NEW SERVER")
                        break
                msg += yield self.launch_process(serv, instance["strategy"], instance["task_id"])
            dingding("AUTO-LAUNCHER", msg)

    @run_on_executor
    def launch_process(self, server_name, strategy, task_id):
        server = get_server(server_name)
        msg = f"create container @ {server_name} for {strategy}\n\n"
        if server:
            container = server.get(strategy)
            if not container:
                r = server.create(
                    IMAGE, # 镜像名
                    strategy, # 策略名
                    f"{working_path}/{task_id}/{strategy}")
                msg += f"result: {r}, "
                
            status = server.start(strategy)
            if status == "running":
                msg += "status: running \n\n"
                now = int(datetime.now().timestamp() * 1000)
                self.db_client.update_one("tasks", {"strategy": strategy, "task_id": task_id}, {"server": server_name, "status": 1})
                self.db_client.update_one("strategy", {"name": strategy}, {"server": server_name})
                self.db_client.insert_one("operation", {"name": strategy, "op": 1, "timestamp": now})
        print(msg)
        return msg

    @run_on_executor
    def okex_accounts(self, active_ac, coins):
        today = datetime.today().strftime("%Y%m%d")
        coins = list(set(map(lambda x: x.split("-")[0], coins)))
        for coin in coins:
            r = OKEX.query_spot_price(f"{coin}-USDT")
            self.db_client.update_one("coin_value", {"date": today, "coin": coin}, {"date" :today, "coin": coin, "value": r})
        
        for vt_ac, symbols in active_ac.items():
            d={}
            for symbol in symbols:
                gateway = OKEX(self.key_chain[vt_ac])
                r = gateway.query_futures_account(symbol[:3])
                d.update({symbol[:3]: float(r["equity"])})

            self.db_client.update_one("account_value", {"date": today, "account": vt_ac}, {"date": today, "account": vt_ac, "FUTURE": d})
        

    @run_on_executor
    def bitmex_accounts(self, active_ac, coins):
        today = datetime.today().strftime("%Y%m%d")
        for coin in coins:
            r = BITMEX.query_futures_price(coin)
            print(r)
            #self.db_client.update_one("coin_value", {"date": today, "coin": coin}, {"date": today, "coin": coin, "value": r})

        for vt_ac, symbols in active_ac.items():
            gateway = BITMEX(self.key_chain[vt_ac])
            r = gateway.query_futures_account("XBt")
            d.update({"XBt":float(r["amount"])})
            print(d)
            #self.db_client.update_one("account_value", {"date": today, "account": vt_ac}, {"date": today, "account": vt_ac, "FUTURE": d})
    
    
    def send_pos(self):
        url = "http://localhost:9999/pos"
        body = urlencode(self.new_pos_dict)
        client = tornado.httpclient.AsyncHTTPClient()
        try:
            client.fetch(url, method = 'POST', body = body)
            self.new_pos_dict = {}
        except Exception as e:
            print("client.fetch failed. reason:",e)

    def get_position_profit(self, coin_values):
        for key, pos in self.pos_dict.items():
            strategy = key.split("-")[0]
            symbol = key.replace(f"{strategy}-","")
            if (pos[0]+pos[1]):
                json_obj = self.db_client.query("orders", {"strategy": strategy})
                stat = get_chart(strategy, json_obj, price_dict=coin_values)
                info = stat["detail"][symbol]
                long_v, short_v = info["position_profit_long"],info["position_profit_short"]
            else:
                long_v = short_v = 0

            self.db_client.update_one(
                        "strategy",
                        {"alias": strategy}, {"profit_rate": {symbol: [long_v,short_v]}}
                    )
            self.new_pos_dict.update({f"{key}-long":long_v,f"{key}-short":short_v})

    def dingding_pos(self, success_orders):
        if success_orders:
            msg = {}
            for od in success_orders:
                stg = od["strategy"] if od["strategy"] else "None"
                ac = msg.get(stg, {})
                msg[stg] = ac
                txt = ac.get(od["account"],[])
                ding = f"> {od['instrument_id']}, {self.mapping[od['type']]}, {od['filled_qty']} @ {od['price_avg']}\n\n"
                txt.append(ding)
                msg[stg][od['account']] = txt
            
            ding = ""
            for stg,detail in msg.items():
                ding+= f"### {stg}\n"
                for ac, txts in detail.items():
                    ding += f"#### - {ac}:\n"
                    for txt in txts:
                        ding += txt
            ding += f"\n {datetime.now().strftime('%y%m%d %H:%M:%S')}"
            dingding("DASHBOARD", ding)
    
    def process_bitmex_orders(self, orders, account, symbol):
        return list(map(lambda x: dict(x,**{
            "account": account,
            "instrument_id": symbol,
            "strategy": x["client_oid"].split("BITMEX")[0],
            "fee": "0",
            "pnl": "0",
            "contract_val": "100",
            "leverage": "100",
            "order_type": "0",
            "state": x["ordStatus"],
            "filled_qty": x["cumQty"],
            "price_avg": x["avgPx"],
            "size": x["orderQty"],
            "order_id": x["orderID"],
            "client_oid": x["clOrdID"],
            "type": x["side"],
            "filled_time": x["transactTime"]
            }), orders))

    @run_on_executor
    def bitmex_orders(self, active_ac, coins):
        filled_orders =[]
        open_orders = []
        for vt_ac, symbols in active_ac.items():
            gateway = BITMEX(self.key_chain[vt_ac])
            for symbol in symbols:
                for state in ["Canceled", "Filled"]:
                    r = gateway.query_futures_orders(symbol, state)
                    if r:
                        filled_orders += self.process_okex_orders(r, vt_ac, symbol)
                r = gateway.query_futures_orders(symbol, "New")
                if r:
                    open_orders += self.process_okex_orders(r, vt_ac, symbol)
                    
        self.process_open_orders(open_orders)
        return filled_orders

    def process_okex_orders(self, orders, account, symbol):
        return list(map(lambda x: dict(x,**{
            "account": account,
            "instrument_id": symbol,
            "strategy": x["client_oid"].split("FUTU")[0]
            }), orders))

    @run_on_executor
    def okex_orders(self, active_ac, coins):
        filled_orders =[]
        open_orders = []
        contract_map, contract_reverse = OKEX.query_futures_instruments()

        for symbol in coins:
            v = OKEX.query_futures_price(contract_map[symbol])
            self.coin_values.update({symbol:v})
        
        for vt_ac, symbols in active_ac.items():
            gateway = OKEX(self.key_chain[vt_ac])
            for symbol in list(symbols):
                for state in ["Canceled", "Filled"]:
                    r = gateway.query_futures_orders(contract_map[symbol],state)
                    if r.get("result", False):
                        filled_orders += self.process_okex_orders(r["order_info"], vt_ac, symbol)
                r = gateway.query_futures_orders(contract_map[symbol], "New")
                if r.get("result", False):
                    open_orders += self.process_okex_orders(r["order_info"], vt_ac, symbol)
        
        self.process_open_orders(open_orders)
        return filled_orders

    @run_on_executor
    def process_filled_orders(self, filled_orders):
        success_orders = []
        filled_orders = list(map(lambda x:dict(x, **{"datetime": convertDatetime(x["timestamp"])}), filled_orders))
        for order in filled_orders:
            if str(order["filled_qty"]) == "0":
                continue
            try:
                self.db_client.insert_one("orders", order)
                self.update_pos(order)
                success_orders.append(order)
            except:
                pass
        print(datetime.now(), "OKEX find:", len(filled_orders), "insert:", len(success_orders))#, "order pending:", len(open_orders))
        return success_orders

    def process_open_orders(self, open_orders):
        open_order_map ={}
        if open_orders:
            for order in open_orders:
                key = f"open-{order['strategy']}-{order['instrument_id']}:{order['account']}"
                qty = open_order_map.get(key, 0)
                open_order_map.update({key: (qty + int(order["size"]))})

            if open_order_map != self.open_order_cache:
                self.open_order_cache, pre = open_order_map, self.open_order_cache
                for order, count in pre.items():
                    if order not in open_order_map.keys():
                        open_order_map.update({order : 0})

                for k, v in open_order_map.items():
                    alias = k.split("-")[1]
                    if alias:
                        self.db_client.update_one(
                            "strategy",
                            {"alias": alias}, {"open_order": {k.replace(f"open-{alias}-",""): v}}
                        )
            else:
                open_order_map ={}
        else:
            for order, count in self.open_order_cache.items():
                open_order_map.update({order: 0})
                alias = order.split("-")[1]
                if alias:
                    self.db_client.update_one(
                        "strategy",
                        {"alias": alias}, {"open_order": {order.replace(f"open-{alias}-",""): 0}}
                    )
            self.open_order_cache = {}
        self.new_pos_dict.update(open_order_map)
        
    def update_pos(self, order):
        strategy, sym, ac = order["strategy"], order["instrument_id"], order["account"]
        direction, vol = order["type"], int(order["filled_qty"])
        vt_ac = f"{sym}:{ac}"
        key = f"{strategy}-{vt_ac}"
        pos_long,pos_short = self.pos_dict.get(key, [0, 0])

        if direction == "1":
            pos_long += vol
            self.new_pos_dict.update({f"long-{key}": pos_long})
        elif direction == "2":
            pos_short += vol
            self.new_pos_dict.update({f"short-{key}": pos_short})
        elif direction == "3":
            pos_long -= vol
            self.new_pos_dict.update({f"long-{key}": pos_long})
        elif direction == "4":
            pos_short -= vol
            self.new_pos_dict.update({f"short-{key}": pos_short})
        elif direction == "BUY":
            if not pos_short:
                pos_long += vol
                self.new_pos_dict.update({f"long-{key}": pos_long})
            else:
                if vol > pos_short:
                    pos_short = 0
                    pos_long += vol - pos_short
                    self.new_pos_dict.update({f"long-{key}": pos_long, f"short-{key}": pos_short})
                else:
                    pos_short -= vol
                    self.new_pos_dict.update({f"short-{key}": pos_short})
        elif direction == "SELL":
            if not pos_long:
                pos_short += vol
                self.new_pos_dict.update({f"short-{key}": pos_short})
            else:
                if vol > pos_long:
                    pos_long = 0
                    pos_short += vol - pos_long
                    self.new_pos_dict.update({f"long-{key}": pos_long, f"short-{key}": pos_short})
                else:
                    pos_long -= vol
                    self.new_pos_dict.update({f"long-{key}":pos_long})

        self.pos_dict[key] = [pos_long, pos_short]
        if strategy:
            self.db_client.update_one(
                "strategy",
                {"alias": strategy},
                {"tradePos": {vt_ac: [pos_long, pos_short]}})

class position_span(object):
    def __init__(self, instrument):
        self.long_price = 0
        self.long_qty = 0
        self.short_price = 0
        self.short_qty = 0
        self.position_profit_long = 0
        self.position_profit_short = 0
        self.used_margin = 0

        self.profit_loss = 0
        self.fee = 0
        self.contract_value = 0
        self.trade_count = 0
        self.winning_count = 0
        self.winning_pnl = 0
        self.position_profit = 0
        
        self.instrument = instrument
        self.leverage = 1
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
        if pnl > 0:
            self.winning_count += 1
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
            self.winning_count += 1
            self.winning_pnl += pnl
        if not self.short_qty:
            self.short_price = 0

    def calculate_position_profit(self, price):
        # 持仓盈亏
        if self.long_qty: 
            profit = ( ( self.contract_value / self.long_price - self.contract_value / price ) * self.long_qty )
            self.position_profit += profit
            margin = self.contract_value * self.long_qty / self.long_price / self.leverage
            self.used_margin += margin
            self.position_profit_long = profit / margin
        if self.short_qty:
            profit = ( ( self.contract_value / price - self.contract_value / self.short_price ) * self.short_qty )
            self.position_profit += profit
            margin = self.contract_value * self.short_qty / self.short_price / self.leverage
            self.used_margin += margin
            self.position_profit_short = profit / margin


# 订单处理
def process_orders(order_data, pos_dict):
    for idx, order in order_data.iterrows():
        order_price = float(order['price_avg'])
        order_qty = int(order['filled_qty'])

        pos_dict.fee += float(order['fee'])
        pos_dict.contract_value = float(order["contract_val"])
        pos_dict.leverage = float(order["leverage"])
        
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
        pos_dict.pnl_list.append([t, pos_dict.profit_loss])
        pos_dict.qty_list.append([t, order_qty])

def get_chart(strategy, json_obj, hist=[], price_dict = {}):
    df = pd.DataFrame(json_obj)
    result = {}
    statistics = {}

    winning_count = 0
    winning_pnl = 0
    total_count = 0
    total_pnl = 0
    if df.size > 0:
        del df["_id"]
        data = df.sort_values(by = "datetime", ascending = True)
        data["vtSymbol"] = data["instrument_id"] + ":" + data["account"]
        instruments = list(set(data["vtSymbol"]))
        if not price_dict:
            contract_map, contract_reverse = OKEX.query_futures_instruments()
        for instrument in instruments:
            per_coin_data = data[data["vtSymbol"] == instrument]
            pos_dict = position_span(instrument)
            process_orders(per_coin_data, pos_dict)
            symbol = instrument.split(":")[0]
            if not price_dict:
                symbol = contract_map[symbol]
                pos_dict.calculate_position_profit(OKEX.query_futures_price(symbol))
            else:
                pos_dict.calculate_position_profit(price_dict[symbol])

            # 缓存策略统计
            result[instrument] = pos_dict

        for instrument, position in result.items():
            net_profit = position.profit_loss + position.fee + position.position_profit
            statistics[instrument] = {
                "symbol" : instrument,
                "trade_count" : position.trade_count,
                "profit_loss" : f"{position.profit_loss:0.4f}",
                "fee" : f"{position.fee:0.4f}",
                "position_profit" : f"{position.position_profit:0.4f}" if position.position_profit else 0,
                "net_profit" : f"{net_profit:0.4f}",
                "holding_long" : position.long_qty,
                "holding_short" : position.short_qty,
                "used_margin": f"{position.used_margin:0.4f}",
                "position_profit_long" : f"{position.position_profit_long: 0.2%}" if position.position_profit_long else 0,
                "position_profit_short" : f"{position.position_profit_short: 0.2%}" if position.position_profit_short else 0,
                "missing_open" : position.missing_open,
                "pnl": position.pnl_list,
                "qty":position.qty_list
            }
            winning_count += position.winning_count
            winning_pnl += position.winning_pnl
            total_count += position.trade_count
            total_pnl += position.profit_loss

    avg_win = 0
    avg_loss = 0
    pnl_ratio = 0
    winning_rate = 0
    if winning_count:
        avg_win = winning_pnl / winning_count
    if total_count - winning_count:
        avg_loss = (total_pnl-winning_pnl) / (total_count-winning_count)
    if avg_loss:
        pnl_ratio = avg_win / avg_loss * -1
    if total_count:
        winning_rate = winning_count / total_count
    
    return {
        "total_count" : total_count,
        "winning_rate" : f"{winning_rate: 0.2%}",
        "pnl_ratio" : f"{pnl_ratio: 0.2f}",
        "running_hist": list(map(lambda x: [x["timestamp"], x["op"]], hist)),
        "detail": statistics
    }