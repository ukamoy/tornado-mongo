import tornado.websocket
import tornado.web
from handlers import BaseHandler
from handlers.query import rotate_query
from dayu.util import filter_name, convertDatetime, dingding
import os,json,traceback,re
from bson import ObjectId
from datetime import datetime
from dayu.performance import run

class dashboard(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        qry = {}
        operation=True
        if not current_user["group"] == "zeus":
            qry = {"Author":current_user["name"]}
            operation=False
        json_obj = self.db_client.query("strategy",qry,[('_id', -1)])
        self.render("dashboard.html", title = "DASHBOARD", data = json_obj,operation = operation)

class strategy(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        stgs = {} if args[0] =='new' else self.db_client.query_one("strategy",{"_id":ObjectId(args[0])}) 
        self.render("strategy.html", title = "New Strategy", data = stgs)
    
    def post(self,*args,**kwargs):
        current_user = self.get_current_user()
        post_values = ['trade_symbols','trade_symbols_ex','trade_symbols_ac',
        'assist_symbols','assist_symbols_ex','assist_symbols_ac']
        stgs = {}
        for v in post_values:
            stgs[v] = self.get_body_arguments(v, None)
        
        sym_list=[]
        stgs["tradeSymbolList"] =[]

        for sym,ex,ac in zip(stgs["assist_symbols"],stgs["assist_symbols_ex"],stgs["assist_symbols_ac"]):
            sym_list.append(f"{sym}:{ex}_{ac}")
        for sym,ex,ac in zip(stgs["trade_symbols"],stgs["trade_symbols_ex"],stgs["trade_symbols_ac"]):
            stgs["tradeSymbolList"].append(f"{sym}:{ex}_{ac}")

        for symbol in list(sym_list):
            if symbol in stgs["tradeSymbolList"]:
                sym_list.remove(symbol)
            
        stgs["symbolList"] = stgs["tradeSymbolList"] + sym_list
        
        stg_set = self.get_argument('strategy_setting', {})
        stgs["strategy_setting"] = eval(stg_set)
        stgs["git_path"] = self.get_argument('git_path', None)
        stgs["name"] = self.get_argument('name', None)
        stgs["strategy_class_name"] = self.get_argument('strategy_class_name', None)
        stgs["alias"] = filter_name(stgs["name"])

        if self.get_argument("_id", None):
            flt={"_id":ObjectId(self.get_argument("_id"))}
            stgs["updatetime"] = datetime.now().strftime("%Y%m%d %H:%M")
            self.db_client.update_one("strategy", flt, stgs)
        else:
            stgs["server"] = "idle"
            stgs["Author"] = current_user["name"]
            stgs["createtime"] = datetime.now().strftime("%Y%m%d %H:%M")
            stgs["updatetime"] = stgs["createtime"]
            self.db_client.insert_one("strategy", stgs)
            self.db_client.insert_one("pos",{"name":stgs["alias"],"long":0,"short":0})
        self.redirect("/dashboard")
    

class task_sheet(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        current_user = self.get_current_user()
        if not args[0]=="all":
            self.db_client.update_one("tasks",{"_id":ObjectId(args[0])},{"status":"withdrawn"})
            dingding("deploy",f"{current_user['name']} withdrawn a task")

        qry = {"Author":current_user["name"]}
        json_obj = self.db_client.query("tasks",qry,[('_id', -1)])
        self.render("task_sheet.html", title = "Task List", data = json_obj)

    def post(self, *args, **kwargs):
        current_user = self.get_current_user()
        task_id = datetime.now().strftime("%Y%m%d%H%M%S")
        stgs = json.loads(self.get_argument('strategies'))

        args = {
            "task_id" : task_id,
            "Author" : current_user["name"],
            "status" : "submitted",
            "strategies" : list(map(lambda x: x["name"],stgs))
            }
        
        self.db_client.insert_one("tasks", args)
        dingding("deploy",f"{current_user['name']} submitted a task \n\nid: {task_id}")
        self.redirect("/dashboard/task_sheet/all")

class chart(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self,*args,**kwargs):
        strategy = args[0]
        qry = {"strategy":strategy,"state":{"$in":["-1","2"]}}
        json_obj = self.db_client.query("orders",qry)
        result = run(json_obj)
        self.render("chart.html", title = strategy, data = result)

class orders(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("name",None):
            name = self.get_argument("name")
            qry={"strategy":name}
            r=self.db_client.query("orders",qry,[('datetime', -1)])
            self.render("orders.html", title = f"{name} ORDERS", data=r,enquiry=False)
        else:
            self.render("orders.html", title = "FIND ORDERS", data="",enquiry=True)
    
    def post(self):
        ac=self.get_argument("ac_name")
        symbol=self.get_argument("symbol")
        state = self.get_argument("state")
        oid=self.get_argument("oid")
        result=[]
        try:
            t= rotate_query()
            r = t.query(f"OKEX_{ac}", symbol, state, oid)
            if r:
                if r.get("result", None):
                    result=r["order_info"]
                    result=list(map(lambda x:dict(x, **{"datetime":convertDatetime(x["timestamp"])}),result))
                else:
                    r["datetime"]=convertDatetime(r["timestamp"])
                    result=[r]
        except:
            pass
        self.render("orders.html", title = "Orders Result", data = result, enquiry=False)

class posHandler(tornado.websocket.WebSocketHandler,BaseHandler):
    users = set()  # 用来存放在线用户的容器
    def open(self):
        self.users.add(self)  # 建立连接后添加用户到容器中
        for strategy,pos in self.pos_dict.items():
            self.on_message(json.dumps({"_name":f"long-{strategy}","_val":pos[0]}))
            self.on_message(json.dumps({"_name":f"short-{strategy}","_val":pos[1]}))
        dt=datetime.now().strftime("%H:%M:%S")
        self.on_message(json.dumps({"_name":"time","_val":dt}))

    def on_close(self):
        self.users.remove(self) # 用户关闭连接后从容器中移除用户
    
    def on_message(self, message):
        for u in self.users:  # 向在线用户广播消息
            u.write_message(message)

    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        print(datetime.now().strftime("%y%m%d %H:%M:%S"),"pos.post", args, self.request.arguments, "body:", self.request.body_arguments)
        if self.get_argument("pos", None):
            pos = json.loads(self.get_argument("pos"))
            for name,val in pos.items():
                self.on_message(json.dumps({"_name":name,"_val":val}))
            dt=datetime.now().strftime("%H:%M:%S")
            self.on_message(json.dumps({"_name":"time","_val":dt}))

handlers = [
    (r"/dashboard", dashboard), 
    (r"/dashboard/strategy/([a-zA-Z0-9]+)", strategy), 
    (r"/dashboard/task_sheet/([a-zA-Z0-9]+)", task_sheet), 
    (r"/pos", posHandler),
    (r"/orders", orders),
    (r"/chart/([a-zA-Z0-9]+)", chart)
]