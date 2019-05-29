import tornado.ioloop
import tornado.web
import tornado.websocket
# from tornado.options import define,options,parse_command_line
from fabric import Connection
import os,json,traceback,re
from datetime import datetime
from dayu.performance import run
from dayu.queryorder import query
from handlers import BaseHandler
from dayu.util.user import Member
from dayu.util.db_conn import db_client
from bson.objectid import ObjectId
from dayu.util.ding import dingding
from dayu.write_settings import update_repo, prepare_stg_files, cp_files

def mongo_obj(id_list):
    ids = []
    for id_ in id_list:
        ids.append(ObjectId(id_))
    return ids
def filter_name(name):
        alpha='abcdefghijklmnopqrstuvwxyz'
        filter_text = "0123456789" + alpha + alpha.upper()
        new_name = filter(lambda ch: ch in filter_text, name)
        return ''.join(list(new_name))[:13]

class home(BaseHandler):
    def get(self):
        current_user = self.get_current_user()
        if current_user:
            self.redirect("/dashboard")
        else:
            self.render("index.html", title = "DAYU SYS", msg=None)
    
    def post(self):
        args = {
            "name":self.get_argument("name",None),
            "pwd":self.get_argument("pwd",None)
        }

        try:
            member = Member()
            member.reload(args['name'], args['pwd'])
            self.clear_all_cookies()
            self.set_cookie(name = "auth", 
                            value = member.auth,
                            expires_days = 15)
            self.redirect("/dashboard")
        except:
            self.render("index.html", title = "DAYU SYS", msg = f"user {args['name']} not exists")

class strategy_performance(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        strategy = args[0]
        db_query = {"strategy":strategy,"state":{"$in":["-1","2"]}}
        try:
            result = run(db_query)
        except:
            result = {}
        self.render("chart.html", title = strategy, data = result)

class query_order(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("query.html", title = "FIND ORDERS",item = None)
    
    def post(self):
        ac=self.get_argument("ac_name")
        symbol=self.get_argument("symbol")
        oid=self.get_argument("oid")
        try:
            result = query(ac, symbol, oid)
        except:
            result = "ERROR"
        self.render("query.html", title = "FIND ORDERS", item = result)

class dashboard(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        if current_user["group"] == "zeus":
            qry = {}
        else:
            qry = {"Author":current_user["name"]}
        json_obj = self.db_client.query("strategy",qry,[('_id', -1)])
        self.render("dashboard.html", title = "DASHBOARD", data = json_obj)

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

        args = {}
        args["task_id"] = task_id 
        args["Author"] = current_user["name"]
        args["status"] = "submitted"
        args["strategies"] = list(map(lambda x: x["name"],stgs))
        
        self.db_client.insert_one("tasks", args)
        dingding("deploy",f"{current_user['name']} submitted a task \nid: {task_id}")
        self.redirect("/dashboard/task_sheet/all")

class deploy(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args, **kwargs):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return self.redirect("/dashboard")

        if args[0] == "all":
            qry = {}
        elif args[0] == "todo":
            qry = {"status":{"$in":["submitted","processing","assigned"]}}

        json_obj = self.db_client.query("tasks",qry,[('_id', -1)])
        self.render("deploy.html", title = "DEPLOYMENT", data = json_obj)
    
    def post(self,*args, **kwargs):
        method = self.get_argument('method')
        _id = self.get_argument('id')
        
        self.db_client.update_one("tasks",{"_id":ObjectId(_id)},{"status":method})
        task = self.db_client.query_one("tasks",{"_id":ObjectId(_id)})
        dingding("deploy", f"{task['Author']}'s task: {task['task_id']}  {method}")

class assignment(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return self.redirect("/dashboard")
        task = self.db_client.query_one("tasks",{"_id":ObjectId(args[0])})
        print(task,args)
        stgs = task["strategies"]
        json_obj = self.db_client.query("strategy",{"name":{"$in":stgs}}) 
        servers = self.db_client.query("server",{},[('_id', -1)])
        serv_name = list(map(lambda x: x["server_name"],servers))
        self.render("task_info.html", title = "ASSIGN SERVER", data = json_obj, serv = serv_name, task_id=args[0])
    
    def post(self,*args,**kwargs):
        server_name = self.get_arguments('server_name')
        _ids = self.get_arguments('_id')
        task_id = self.get_argument('task_id')
        for serv, _id in zip(server_name, _ids):
            self.db_client.update_one("strategy",{"_id":ObjectId(_id)},{"server":serv})

        msg = self.assign_task(_ids, task_id)
        self.db_client.update_one("tasks",{"_id":ObjectId(task_id)},{"status":"assigned"})
        dingding("deploy",f"task: {task_id} assigned \n {msg}")
        self.redirect("/deploy/list/todo")

    def assign_task(self, _ids, task_id):
        json_obj = self.db_client.query("strategy",{"_id":{"$in":mongo_obj(_ids)}})
        
        server_names = list(set(map(lambda x: x["server"],json_obj)))
        servers = self.db_client.query("server",{"server_name":{"$in":server_names}})
        
        key_chain = {}
        keys=[]
        key_list = list(map(lambda x: x['trade_symbols_ac']+x['assist_symbols_ac'], json_obj))
        for key in key_list:
            keys+=key
        keys = self.db_client.query("account",{"name":{"$in":list(set(keys))}})

        for key in keys:
            key_chain.update({key["name"]:[key["apikey"],key["secretkey"],key["passphrase"]]})
        
        msg = update_repo()
        prepare_stg_files(json_obj, task_id, key_chain)

        for server in servers:
            c = Connection(f"dayu@{server['server_ip']}", connect_kwargs = {"password":"Xinger520"})
            msg += cp_files(c, server['server_name'], task_id)

        return msg

class server(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return self.redirect("/dashboard")

        json_obj = self.db_client.query("server",{},[('_id', -1)])
        self.render("server.html", title = "SERVER MGMT", data = json_obj)
    
    def post(self):
        branch = self.get_argument("branch")
        server_ips = json.loads(self.get_argument("server_ips"))
        server_history = {}
        msg = f"update vnpy to {branch}\n"
        for server in server_ips:
            c = Connection(f"dayu@{server['id']}", connect_kwargs = {"password":"Xinger520"})
            USER_HOME = "/home/dayu"
            with c.cd(f"{USER_HOME}/Documents/vnpy_fxdayu"):
                c.run(f"yes | {USER_HOME}/anaconda3/bin/pip uninstall vnpy_fxdayu")
                c.run(f"git pull origin {branch}")
                c.run(f"git checkout {branch}")
                
                c.run(f"{USER_HOME}/anaconda3/bin/python -E setup.py install")
                cmd_rtn = c.run("git reflog")
                ref_tag = cmd_rtn.stdout.split("\n")[0].split(" ")[0]
                msg += f"> 服务器 {server['name']} 已经更新到了 {ref_tag} 版本 \n\n"
                server_history[server['name']] = f"{datetime.now().strftime('%Y%m%d %H:%M:%S')} 更新 {ref_tag} 版本"

        for k,v in server_history.items():
            self.db_client.update_one("server",{"server_name":k},{"history":v})
        dingding("deploy",msg)
        self.redirect("/deploy/server")

class ding(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        if self.get_argument("method", None):
            qry = self.get_argument("method")
            json_obj={} if qry=="new" else self.db_client.query("ding",{})
            self.render("ding.html",title = "DINGDING",data = json_obj,edit=None)
        else:
            qry = self.get_argument("name")
            json_obj= self.db_client.query_one("ding",{"name":qry})
            self.render("ding.html",title = "DINGDING",data = {},edit=json_obj)

    def post(self,*args,**kwargs):
        if self.get_argument("delete",None):
            self.db_client.delete_one("ding",{"name":self.get_argument("delete")})
        else:
            old_name=self.get_argument("old_name",None)
            qry = {
                "name":self.get_argument("ding_name",None),
                "token":self.get_argument("ding_token",None)
                }
            self.db_client.update_one("ding",{"name":old_name},qry)
        self.redirect("/ding?method=all")

class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        print("conn get\n",args, self.request.__dict__)
        if self.get_argument("checkName", None):
            qry = filter_name(self.get_argument("checkName"))
            r = self.db_client.query_one("strategy",{"alias":qry})
        elif self.get_argument("checkUser", None):
            qry = self.get_argument("checkUser")
            r = self.db_client.query_one("user",{"name":qry})
        elif self.get_argument("checkDing", None):
            qry = self.get_argument("checkDing")
            r = self.db_client.query_one("ding",{"name":qry})
        elif self.get_argument("task_id", None):
            t = self.get_argument("task_id")
            n = self.get_argument("stg_name")
            qry = {"_id":ObjectId(t)}
            r = self.db_client.query_one("tasks",qry)
            running_stg = r["running"].append(n)
            self.db_client.update_one("tasks",qry,{"running":running_stg})
        elif self.get_argument("getAccount", None):
            self.finish(self.ac_dict)
            return
        elif self.get_argument("orders", None):
            r=json.loads(self.get_argument("orders"))
            print(r)
            return
        if r:
            msg = True
        else:
            msg = False
        self.finish(json.dumps(msg))

class posHandler(tornado.websocket.WebSocketHandler,BaseHandler):
    users = set()  # 用来存放在线用户的容器
    def open(self):
        self.users.add(self)  # 建立连接后添加用户到容器中
        for strategy,pos in self.pos_dict.items():
            self.on_message(json.dumps({"_name":f"long-{strategy}","_val":pos[0]}))
            self.on_message(json.dumps({"_name":f"short-{strategy}","_val":pos[1]}))

    def on_close(self):
        self.users.remove(self) # 用户关闭连接后从容器中移除用户
    
    def on_message(self, message):
        for u in self.users:  # 向在线用户广播消息
            u.write_message(message)

    def post(self,*args,**kwargs):
        print("conn post\n",args, self.request.__dict__)
        if self.get_argument("orders", None):
            orders = json.loads(self.get_argument("orders"))
            self.db_client.insert_many("orders",orders)
            for order in orders:
                strategy,direction,vol = order["name"],order["type"],order["qty"]
                pos_long,pos_short = self.pos_dict.get(strategy,[0,0])

                if direction =="1":
                    pos_long += vol
                elif direction =="2":
                    pos_short += vol
                elif direction =="3":
                    pos_long -= vol
                elif direction =="4":
                    pos_short -= vol

                self.on_message(json.dumps({"_name":f"long-{strategy}","_val":pos_long}))
                self.on_message(json.dumps({"_name":f"short-{strategy}","_val":pos_short}))
                self.pos_dict[strategy] = [pos_long,pos_short]
            for stg,pos in self.pos_dict.items():
                self.db_client.update_one("pos",{"name":stg},{"name":stg,"long":pos[0],"short":pos[1]})

#---------------------------------------------------------------------

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'template_path':os.path.join(os.path.dirname(__file__), "templates"),
    "login_url":"/"
}

application = tornado.web.Application([
    (r"/", home), 
    (r"/dashboard", dashboard), 
    (r"/dashboard/strategy/([a-zA-Z0-9]+)", strategy), 
    (r"/dashboard/task_sheet/([a-zA-Z0-9]+)", task_sheet), 
    (r"/deploy/list/(all|todo|work)", deploy),
    (r"/deploy/assignment/([a-zA-Z0-9]+)", assignment),
    (r"/deploy/server", server),
    (r"/query_order", query_order),
    (r"/chart/([a-zA-Z0-9]+)", strategy_performance),
    (r"/dy", MainHandler), 
    (r"/ding", ding), 
    (r"/pos", posHandler)
],**settings)

if __name__ == "__main__":
    application.listen(9999)
    tornado.ioloop.IOLoop.instance().start()