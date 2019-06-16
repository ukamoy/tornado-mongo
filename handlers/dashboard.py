import tornado.websocket
import tornado.web
from handlers import BaseHandler
from handlers.query import rotate_query, get_chart
from dayu.util import filter_name, convertDatetime, dingding
from dayu.write_settings import update_repo, prepare_stg_files
import os,json,traceback,re
from bson import ObjectId
from datetime import datetime

class dashboard(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        current_user = self.get_current_user()
        qry = {"Author":current_user["name"]}
        show = ""
        if current_user["group"] in ["xinge","zeus"]:
            show="all"
            if self.get_argument("display",None):
                qry = {}
                show="mine"

        json_obj = self.db_client.query("strategy",qry,[('_id', -1)])
        self.render("dashboard.html", title = "DASHBOARD", data=json_obj,show=show)

class strategy(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        stgs = {} if args[0] =='new' else self.db_client.query_one("strategy",{"_id":ObjectId(args[0])}) 
        self.render("strategy.html", title = "Strategy", data = stgs)

    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        current_user = self.get_current_user()
        post_values = ['trade_symbols','trade_symbols_ex','trade_symbols_ac',
        'assist_symbols','assist_symbols_ex','assist_symbols_ac']
        stgs = {}
        for v in post_values:
            stgs[v] = self.get_body_arguments(v, None)
        
        sym_list=[]
        stgs["tradeSymbolList"] =[]
        stgs["tradePos"] = {}

        for sym,ex,ac in zip(stgs["assist_symbols"],stgs["assist_symbols_ex"],stgs["assist_symbols_ac"]):
            sym_list.append(f"{sym}:{ex}_{ac}")
        for sym,ex,ac in zip(stgs["trade_symbols"],stgs["trade_symbols_ex"],stgs["trade_symbols_ac"]):
            symbol = f"{sym}:{ex}_{ac}"
            stgs["tradeSymbolList"].append(symbol)
            stgs["tradePos"].update({symbol:[0,0]})


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
    

class tasks(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        current_user = self.get_current_user()
        if args[0]=="all":
            qry = {"Author":current_user["name"]}
            admin = False
            if current_user["group"]=="zeus":
                qry={}
                admin=True
            json_obj = self.db_client.query("tasks",qry,[('_id', -1)])
            self.render("tasks.html", title = "Task List", data = json_obj,admin=admin)
        else:
            task = self.db_client.query_one("tasks",{"task_id":args[0]})
            json_obj = self.db_client.query("strategy",{"name":{"$in":task["strategies"]}}) 
            servers = self.db_client.query("server",{},[('_id', -1)])
            serv_name = list(map(lambda x: x["server_name"], servers))
            self.render("task_info.html", title = f"TASK {args[0]}", data = json_obj, serv = serv_name, Author = task['Author'], task_id=args[0], status=task["status"])
  
    def post(self, *args, **kwargs):
        current_user = self.get_current_user()
        task_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        stgs = list(self.request.arguments.keys())
        
        args = {
            "task_id" : task_id,
            "Author" : current_user["name"],
            "status" : "submitted",
            "strategies" : stgs
            }
        msg = self.assign_task(stgs,task_id)
        self.db_client.insert_one("tasks", args)
        dingding("TASK",f"{args['Author']} submitted new task \n\nid: {args['task_id']}\n\n{msg}")
        self.finish(json.dumps(task_id))

    def assign_task(self, stgs, task_id):
        # get strategies
        json_obj = self.db_client.query("strategy",{"name":{"$in":stgs}})
        
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
        strategy = args[0]
        self.render("chart.html", title = f"{strategy} Chart")
    def post(self,*args,**kwargs):
        strategy = args[0]
        json_obj = self.db_client.query("orders",{"strategy":strategy})
        stat = get_chart(strategy, json_obj)
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
        self.render("orders.html", title = f"{name} ORDERS", data=r, enquiry=enquiry)
        
    @tornado.gen.coroutine
    def post(self):
        result = []
        t = rotate_query()
        r = t.query(
            f"OKEX_{self.get_argument('ac_name')}", 
            self.get_argument("symbol"), 
            self.get_argument("state"), 
            self.get_argument("oid"))
        if r:
            if r.get("result", None):
                result=list(map(lambda x:dict(x, **{"datetime":convertDatetime(x["timestamp"])}),r["order_info"]))
            else:
                r["datetime"]=convertDatetime(r["timestamp"])
                result=[r]
        self.render("orders.html", title = "Orders Result", data = result, enquiry=False)

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
    (r"/dashboard/strategy/([a-zA-Z0-9]+)", strategy), 
    (r"/dashboard/tasks/([a-zA-Z0-9]+)", tasks), 
    (r"/pos", posHandler),
    (r"/orders", orders),
    (r"/chart/([a-zA-Z0-9]+)", chart),
]