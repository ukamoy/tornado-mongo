from pymongo import MongoClient
import pandas as pd
import os
from datetime import datetime,timedelta
import json
import requests

REST_HOST = "https://www.okex.com"
# MONGO_URI = "mongodb://dayu:Xinger520@localhost:27017/dayu-orders"
MONGO_URI = "mongodb://192.168.0.104:27017"
DB_NAME = "dayu-orders"
ATT_PATH = f"{os.getcwd()}/tmp"
class position_span(object):
    def __init__(self, instrument):
        self.long_price = 0
        self.long_qty = 0
        self.short_price = 0
        self.short_qty = 0

        self.profit_loss = 0
        self.fee = 0
        self.trade_count = 0
        self.position_profit = 0
        self.instrument = instrument
        self.contract_value = 0
        self.missing_open = ""
        self.pnl_dict = {}

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
        self.profit_loss += (( self.contract_value / self.long_price - self.contract_value / price ) * qty)
        self.long_qty -= qty
        if not self.long_qty:
            self.long_price = 0

    def cover_short_holding(self, price, qty):
        #  平空盈亏： (合约面值 / 平均平仓价格 – 合约面值 / 结算基准价) * 平仓数量 
        self.trade_count += 1
        self.profit_loss += (( self.contract_value / price - self.contract_value / self.short_price ) * qty)
        self.short_qty -= qty
        if not self.short_qty:
            self.short_price = 0

    def calculate_position_profit(self, price):
        # 持仓盈亏
        if self.long_qty:
            self.position_profit += ( ( self.contract_value / self.long_price - self.contract_value / price ) * self.long_qty )
        if self.short_qty:
            self.position_profit += ( ( self.contract_value / price - self.contract_value / self.short_price ) * self.short_qty )

# 获取剩余持仓结算价格
def query_price(instrument):
    url = f'{REST_HOST}/api/futures/v3/instruments/{instrument}/ticker'
    r = requests.get(url,timeout = 10)
    result = json.loads(r.content)
    return float(result["last"])

# 订单处理
def process_orders(order_data, pos_dict):
    for idx, order in order_data.iterrows():
        order_price = float(order['price_avg'])
        order_qty = float(order['filled_qty'])
        if not order_qty:
            continue

        pos_dict.contract_value = int(order['contract_val'])
        pos_dict.account = order['account']
        pos_dict.fee += float(order['fee'])
        
        if str(order['type']) == "1":
            pos_dict.add_up_buy_orders(order_price, order_qty)
        
        elif str(order['type']) == "2":
            pos_dict.add_up_short_orders(order_price, order_qty)
        
        elif str(order['type']) == "3":
            if pos_dict.long_qty < int(order_qty):
                pos_dict.missing_open += f"{order['datetime']}, hold_long:{pos_dict.long_qty} vs. sell_qty:{order_qty}\n"
                continue
            pos_dict.sell_long_holding(order_price, order_qty)
        
        elif str(order['type']) == "4":
            if pos_dict.short_qty < int(order_qty):
                pos_dict.missing_open += f"{order['datetime']}, hold_short:{pos_dict.short_qty} vs. cover_qty:{order_qty}\n"
                continue
            pos_dict.cover_short_holding(order_price, order_qty)
        
        pos_dict.pnl_dict[order['datetime']] = pos_dict.profit_loss


# 统计视图
def result_presentation(strategy_result):
    import matplotlib.pyplot as plt
    from pandas.plotting import register_matplotlib_converters
    register_matplotlib_converters()
    result = {}
    
    for strategy, performance in strategy_result.items():
        for instrument, position in performance.items():
            net_profit = position.profit_loss + position.fee + position.position_profit

            # 绘图
            plt.figure(figsize = (8,4))
            plt.title(f"{strategy} pnl curve")
            dt = position.pnl_dict.keys()
            pnl = position.pnl_dict.values()
            plt.plot(dt, pnl, 'r--', label = instrument)
            plt.legend()

            plt.xlabel('datetime')
            plt.ylabel('pnl')
            plt.xticks(rotation=25, fontsize=8)
            plt.savefig(f'static/image/{strategy}-{instrument}.png')
            plt.close()

            result[instrument] = {
                "strategy" : strategy,
                "symbol" : instrument,
                "account" : position.account,
                "trade_count" : position.trade_count,
                "profit_loss" : position.profit_loss,
                "fee" : position.fee,
                "position_profit" : position.position_profit,
                "net_profit" : net_profit,
                "holding_long" : position.long_qty,
                "holding_short" : position.short_qty,
                "missing_open" : position.missing_open,
                "img" : f"{strategy}-{instrument}.png",

            }

    return result

def run(DB_QUERY):
    result = {}
    db = MongoClient(MONGO_URI)[DB_NAME]
    Cursor = db["future"].find(DB_QUERY)
    df = pd.DataFrame(list(Cursor))
    print(df.shape,DB_QUERY)

    if df.size > 0:
        data = df[["datetime","account","strategy","instrument_id","filled_qty","price_avg","fee","type","contract_val","order_type"]]
        data = data.sort_values(by = "datetime", ascending = True)
        
        # 缓存结算价格
        currency_list = list(set(data["instrument_id"]))
        price_dict = {}
        for instrument in currency_list:
            price_dict[instrument] = query_price(instrument)

        strategy = DB_QUERY["strategy"]
        result[strategy] ={}
        data["vtSymbol"] = data["instrument_id"]+":"+data["account"]
        instruments = list(set(data["vtSymbol"]))
        for instrument in instruments:
            sym = instrument.split(":")[0]
            per_coin_data = data[data["instrument_id"] == sym]
            pos_dict = position_span(instrument)
            process_orders(per_coin_data, pos_dict)
            pos_dict.calculate_position_profit(price_dict[sym])

            # 缓存策略统计
            result[strategy][instrument] = pos_dict

    strategy_result = result_presentation(result)
    return strategy_result

def get_stg_list(DB_QUERY):
    db = MongoClient(MONGO_URI)[DB_NAME]
    Cursor = db["future"].find(DB_QUERY)
    df = pd.DataFrame(list(Cursor))
    stg_list = []
    if df.size > 0:
        data = df[["datetime","account","strategy","instrument_id","filled_qty","price_avg","fee","type","contract_val","order_type"]]
        data.sort_values(by = "datetime", ascending = True, inplace=True)
        
        stg_list = list(set(data["strategy"]))
    return stg_list