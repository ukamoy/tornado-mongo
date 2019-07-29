import tornado.websocket
import tornado.web
from handlers import BaseHandler
from handlers.query import get_chart
from dayu.util import filter_name, convertDatetime, dingding
from dayu.exchange import OKEX
from dayu.write_settings import update_repo, prepare_stg_files
import os,json,traceback,re
from bson import ObjectId
from datetime import datetime

class dashboard(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        qry = {"Author":self.user["name"]}
        show = ""
        if self.user.get("group","") in ["xinge","zeus"]:
            show="all"
            if self.get_argument("display",None):
                qry = {}
                show="mine"

        json_obj = self.db_client.query("strategy",qry,[('updatetime', -1)])
        self.render("dashboard.html", user=self.user, title = "DASHBOARD", data=json_obj,show=show)

class strategy(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        strategy = {} if args[0] =='new' else self.db_client.query_one("strategy",{"name":args[0]}) 
        s=0
        if strategy:
            for pos in strategy["tradePos"].values():
                s+=(pos[0]+pos[1])
        self.render("strategy.html", user=self.user, title = "Strategy", data = strategy, pos=s)
    
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        post_values = ['trade_symbols','trade_symbols_ex','trade_symbols_ac',
        'assist_symbols','assist_symbols_ex','assist_symbols_ac']
        strategy = {}
        for v in post_values:
            strategy[v] = self.get_body_arguments(v, None)
        
        sym_list=[]
        strategy["tradeSymbolList"] =[]
        strategy["tradePos"] = {}
        strategy["open_order"] ={}

        for sym,ex,ac in zip(strategy["assist_symbols"],strategy["assist_symbols_ex"],strategy["assist_symbols_ac"]):
            sym_list.append(f"{sym}:{ex}_{ac}")
        for sym,ex,ac in zip(strategy["trade_symbols"],strategy["trade_symbols_ex"],strategy["trade_symbols_ac"]):
            symbol = f"{sym}:{ex}_{ac}"
            strategy["tradeSymbolList"].append(symbol)
            strategy["tradePos"].update({symbol:[0,0]})
            strategy["open_order"].update({symbol:0})

        for symbol in list(sym_list):
            if symbol in strategy["tradeSymbolList"]:
                sym_list.remove(symbol)
        strategy["symbolList"] = strategy["tradeSymbolList"] + sym_list
        
        stg_set = self.get_argument('strategy_setting', {})
        strategy["strategy_setting"] = eval(stg_set)
        strategy["git_path"] = self.get_argument('git_path', None)
        strategy["name"] = self.get_argument('name', None)
        strategy["strategy_class_name"] = self.get_argument('strategy_class_name', None)
        strategy["alias"] = filter_name(strategy["name"])

        if self.get_argument("_id", None):
            flt={"_id":ObjectId(self.get_argument("_id"))}
            strategy["updatetime"] = datetime.now().strftime("%Y%m%d %H:%M")
            self.db_client.update_one("strategy", flt, strategy)
        else:
            strategy["server"] = "idle"
            strategy["Author"] = self.user["name"]
            strategy["createtime"] = datetime.now().strftime("%Y%m%d %H:%M")
            strategy["updatetime"] = strategy["createtime"]
            self.db_client.insert_one("strategy", strategy)
        self.redirect("/dashboard")
    

class tasks(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        admin = True

        if args[0]=="instance":
            title = "INSTANCE"
            qry = {"status":{"$in":[0,1]}}
            servers = self.db_client.query("server",{},[('_id', -1)])
            serv_name = list(map(lambda x: x["server_name"], servers))
        elif args[0]=="archiver":
            qry = {"status":-1}
            title = "ARCHIVER"
            serv_name = None
        else:
            return self.finish()

        if self.user.get("group","") != "zeus":
            qry.update({"Author" : self.user["name"]})
            admin = False
        
        json_obj = self.db_client.query("tasks",qry,[('_id', -1)])
        self.render("tasks.html", user=self.user, title = title, data = json_obj, serv = serv_name,admin=admin)
    
    @tornado.web.authenticated
    def post(self, *args, **kwargs):
        task_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        stg_list = list(self.request.arguments.keys())
        json_obj = self.db_client.query("strategy",{"name":{"$in":stg_list}})
        for strategy in json_obj:
            args = {
                "task_id": task_id,
                "Author": self.user["name"],
                "status": 0,
                "server": "idle",
                "strategy": strategy["name"],
                "account": strategy["trade_symbols_ac"]
                }
            self.db_client.insert_one("tasks", args)

        msg = self.assign_task(stg_list,task_id)
        dingding("TASK",f"{args['Author']} Create Task \n\nid: {args['task_id']}\n\n{msg}")
        self.finish(json.dumps(task_id))

    def assign_task(self, stg_list, task_id):
        # get strategies
        json_obj = self.db_client.query("strategy",{"name":{"$in":stg_list}})
        
        # gether required keys
        key_chain = {}
        key_list = list(map(lambda x: x['trade_symbols_ac'] + x['assist_symbols_ac'], json_obj))
        key_list = [i for k in key_list for i in k]
        key_list = self.db_client.query("account",{"name":{"$in":list(set(key_list))}})

        for key in key_list:
            key_chain.update({key["name"]:[key["apikey"],key["secretkey"],key["passphrase"],key["future_leverage"]]})
        
        # update repo
        msg = update_repo()
        try:
            prepare_stg_files(json_obj, task_id, key_chain)
            stg_names = list(map(lambda x: x["name"],json_obj))
            msg+= f"> strategy settings ready for : \n\n{stg_names}"
        except Exception as e:
            msg = False
        
        return msg
class chart(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        self.render("chart.html", user=self.user, title = f"{args[0]} Chart")
    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        strategy = args[0]
        json_obj = self.db_client.query("orders",{"strategy":filter_name(strategy)})
        hist = self.db_client.query("operation",{"name":strategy})
        stat = get_chart(strategy, json_obj, hist)
        self.finish(json.dumps(stat))

class orders(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        r = {}
        enquiry = True
        name = "FIND"
        if self.get_argument("name",None):
            name=self.get_argument("name")
            r=self.db_client.query("orders",{"strategy":name},[('datetime', -1)])
            enquiry=False
        self.render("orders.html", user=self.user, title = f"{name} ORDERS", data=r, enquiry=enquiry)
        
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self):
        result = []
        account_info = self.db_client.query_one("account",{"name":self.get_argument('ac_name')})
        symbol = self.get_argument("symbol")
        oid = self.get_argument("oid")
        gateway = OKEX(account_info)
        if oid:
            r = gateway.query_futures_monoOrder(symbol, oid)
        else:
            r = gateway.query_futures_orders(symbol, self.get_argument("state"))
        
        if r:
            if r.get("result", None):
                result=list(map(lambda x:dict(x, **{"datetime":convertDatetime(x["timestamp"])}),r["order_info"]))
            else:
                r["datetime"]=convertDatetime(r["timestamp"])
                result=[r]
        self.render("orders.html", user=self.user, title = "Orders Result", data = result, enquiry=False)

class posHandler(tornado.websocket.WebSocketHandler,BaseHandler):
    users = set()  # 用来存放在线用户的容器
    def open(self):
        self.users.add(self)  # 建立连接后添加用户到容器中
        self.on_message(json.dumps({"_name":"time","_val":datetime.now().strftime("%H:%M:%S")}))

    def on_close(self):
        self.users.remove(self) # 用户关闭连接后从容器中移除用户
    
    def on_message(self, message):
        for u in self.users:  # 向在线用户广播消息
            u.write_message(message)

    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        print(datetime.now().strftime("%y%m%d %H:%M:%S"),"pos.post body:", self.request.body_arguments)
        pos = self.request.arguments
        if pos:
            for name,val in pos.items():
                self.on_message(json.dumps({"_name":name,"_val":self.get_argument(name)}))

        self.on_message(json.dumps({"_name":"time","_val":datetime.now().strftime("%H:%M:%S")}))

handlers = [
    (r"/dashboard", dashboard), 
    (r"/dashboard/strategy/([a-zA-Z0-9_]+)", strategy), 
    (r"/dashboard/tasks/([a-zA-Z0-9]+)", tasks), 
    (r"/pos", posHandler),
    (r"/orders", orders),
    (r"/chart/([a-zA-Z0-9_-]+)", chart),
]