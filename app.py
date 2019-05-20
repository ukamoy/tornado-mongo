import tornado.ioloop
import tornado.web
# from tornado.options import define,options,parse_command_line
from fabric import Connection
import os,json,traceback,re
from datetime import datetime
from dayu.performance import run, get_stg_list
from dayu.queryorder import query
from handlers import BaseHandler
from dayu.util.user import Member
from dayu.util.db_conn import db_client
from bson.objectid import ObjectId
from dayu.util.ding import dingding

def mongo_obj(id_list):
    ids = []
    for id_ in id_list:
        ids.append(ObjectId(id_))
    return ids

class MainHandler(BaseHandler):
    def get(self):
        current_user = self.get_current_user()
        if current_user:
            self.redirect("/dashboard")
        else:
            self.render("index.html", title = "DAYU SYS", msg=None)
    
    def post(self):
        post_values = ['name','pwd']
        args = {}
        for v in post_values:
            args[v] = self.get_argument(v, None)

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
    def get(self):
        query = {"state":{"$in":["-1","2"]}}
        stg_list = get_stg_list(query)
        self.render("performance.html", title = "DAYU", items=stg_list)
    
    def post(self):
        strategy=self.get_argument("strategy_name")
        db_query = {"strategy":strategy,"state":{"$in":["-1","2"]}}
        try:
            result = run(db_query)
        except:
            result = "STARTEGY NAME ERROR"
        self.render("performance.html", title = strategy, items = result)

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
        stg = {} if args[0] =='new' else self.db_client.query_one("strategy",{"_id":ObjectId(args[0])}) 
        self.render("strategy.html", title = "New Strategy", data = stg, account = self.account_list )
    
    def post(self,*args,**kwargs):
        current_user = self.get_current_user()
        post_values = ['git_path','name','strategy_class_name',
        'trade_symbols','assist_symbols','account_name']
        stgs = {}
        for v in post_values:
            stgs[v] = self.get_argument(v, None)

        stg_set = self.get_argument('strategy_setting', {})
        stgs["strategy_setting"] = eval(stg_set)

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
        self.redirect("/dashboard")
        self.checkout_git(stgs["git_path"])

    def checkout_git(self, gitpath):
        pass


# class waitlist(BaseHandler):
#     @tornado.web.authenticated
#     def get(self):
#         current_user = self.get_current_user()
#         qry = {"name":current_user["name"]}
#         r = self.db_client.query_one("user",qry)
#         if r:
#             qry = {"_id":{"$in":mongo_obj(r["waitlist"])}}
#             json_obj = self.db_client.query("strategy",qry,[('_id', -1)])
#         else:
#             json_obj = {}
#         self.render("waitlist.html", title = "waitlist",data = json_obj)

#     def post(self):
#         current_user = self.get_current_user()
#         flt = {"name":current_user["name"]}
#         r = self.db_client.query_one("user",flt)
#         waitlist = []
#         if r:
#             waitlist = r["waitlist"]
#         if self.get_argument('delete',None):
#             tmp = self.get_argument('delete')
#             waitlist.remove(self.get_argument('delete'))
#         elif self.get_argument('strategy_ids', None):
#             items = json.loads(self.get_argument('strategy_ids'))
#             for item in items:
#                 waitlist.append(item["id"])
#         qry= {"waitlist":list(set(waitlist))}
#         self.db_client.update_one("user",flt, qry)
#         self.redirect("/dashboard")

class task_sheet(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        current_user = self.get_current_user()
        if not args[0]=="all":
            self.db_client.update_one("tasks",{"_id":ObjectId(args[0])},{"status":"cancelled"})
            #self.redirect("/dashboard/task_sheet/all")
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
        dingding("deploy",f"{current_user['name']} submitted a task")
        # self.db_client.update_one("user",{"name":current_user["name"]},{"waitlist":[]})
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
        current_user = self.get_current_user()
        task = self.db_client.query_one("tasks",{"_id":ObjectId(_id)})
        dingding("deploy", f"{task['Author']}'s task: {task['task_id']}  {method}")


class assignment(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return self.redirect("/dashboard")
        task = self.db_client.query_one("tasks",{"_id":ObjectId(args[0])})
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
        qry = list(map(lambda x: x['account_name'], json_obj))
        keys = self.db_client.query("account",{"name":{"$in":qry}})
        for key in keys:
            key_chain.update({key["name"]:[key["apikey"],key["secretkey"],key["passphrase"]]})
        
        from dayu.write_settings import update_repo, prepare_stg_files, cp_files
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
        msg = f"update vnpy to {branch}"
        for server in server_ips:
            c = Connection(f"dayu@{server['id']}", connect_kwargs = {"password":"Xinger520"})
            USER_HOME = "/home/dayu"
            with c.cd(f"{USER_HOME}/Documents/vnpy_fxdayu"):
                # c.run(f"yes | {USER_HOME}/anaconda3/bin/pip uninstall vnpy_fxdayu")
                c.run(f"git pull origin {branch}")
                c.run(f"git checkout {branch}")
                
                # c.run(f"{USER_HOME}/anaconda3/bin/python -E setup.py install")
                cmd_rtn = c.run("git reflog")
                ref_tag = cmd_rtn.stdout.split("\n")[0].split(" ")[0]
                msg += f"> 服务器 {server['name']} 已经更新到了 {ref_tag} 版本 \n\n"
                server_history[server['name']] = f"{datetime.now().strftime('%Y%m%d %H:%M:%S')} 更新 {ref_tag} 版本"

        for k,v in server_history.items():
            self.db_client.update_one("server",{"server_name":k},{"history":v})
            dingding("deploy",msg)
        self.redirect("/deploy/server")
#---------------------------------------------------------------------

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'template_path':os.path.join(os.path.dirname(__file__), "templates"),
    "login_url":"/"
}

application = tornado.web.Application([
    (r"/", MainHandler), 
    (r"/dashboard", dashboard), 
    (r"/dashboard/strategy/([a-zA-Z0-9]+)", strategy), 
    # (r"/dashboard/waitlist", waitlist), 
    (r"/dashboard/task_sheet/([a-zA-Z0-9]+)", task_sheet), 
    (r"/deploy/list/(all|todo|work)", deploy),
    (r"/deploy/assignment/([a-zA-Z0-9]+)", assignment),
    (r"/deploy/server", server),
    (r"/query_order", query_order),
    (r"/strategy_performance", strategy_performance),
],**settings)

if __name__ == "__main__":
    application.listen(9999)
    tornado.ioloop.IOLoop.instance().start()