import tornado.web
from handlers import BaseHandler
from dayu.util import mongo_obj,server_conn, dingding
import os,json,traceback,re
from dayu.write_settings import update_repo, prepare_stg_files, cp_files

class assignment(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        if not self.user.get("group","") == "zeus":
            return self.redirect("/dashboard")
        task = self.db_client.query("tasks",{"task_id":args[0]})
        stg_list = list(map(lambda x: x["strategy"],task))
        json_obj = self.db_client.query("strategy",{"name":{"$in":stg_list}}) 
        servers = self.db_client.query("server",{},[('_id', -1)])
        serv_name = list(map(lambda x: x["server_name"], servers))
        self.render("assign.html", user=self.user, title = "ASSIGN SERVER (Remote File Dispatcher)", data = json_obj, serv = serv_name, task_id=args[0])
    
    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        # update db for assigned strategy
        server_names = self.get_arguments('server_names')
        stg_names = self.get_arguments('stg_names')
        for serv, stg_name in zip(server_names, stg_names):
            self.db_client.update_one("strategy",{"name":stg_name},{"server":serv})
        
        # prepare strategy
        task_id = self.get_argument('task_id')
        servers = self.db_client.query("server",{"server_name":{"$in":server_names}})
        for server in servers:
            c = server_conn(server["server_ip"])
            msg = cp_files(c, server["server_name"], task_id)
        dingding("deploy", f"task {task_id} assigned by file transfer\n\n {msg}")
        self.redirect(f"/deploy/assignment/{task_id}")

class server(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if not self.user.get("group", "") == "zeus":
            return self.redirect("/dashboard")

        json_obj = self.db_client.query("server",{},[('_id', -1)])
        self.render("server.html", user=self.user, title = "SERVER MGMT", data = json_obj)
    @tornado.gen.coroutine
    def post(self):
        branch = self.get_argument("branch")
        server_ips = json.loads(self.get_argument("server_ips"))
        server_history = {}
        msg = f"update vnpy to {branch}\n"
        for server in server_ips:
            c = server_conn(server['id'])
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

class account(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        accounts = self.db_client.query("account_value",{})
        ac_list = list(set(map(lambda x: x["account"], accounts)))
        self.render("account.html", user=self.user, title = f"Account Chart", ac_list=sorted(ac_list))
    
    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        ac_hist = self.db_client.query("account_value",{"account":self.get_argument("query")})
        b=list(map(lambda x: [x["date"],x["FUTURE"]],ac_hist))
        c=list(map(lambda x: x[1],b))
        coins=sum(list(map(lambda x: list(x.keys()),c)),[])
        coin_dict={}
        usdt_dict = {}
        for k in list(set(coins)):
            prices = self.db_client.query("coin_value",{"coin":k})
            p={d["date"]:d["value"] for d in prices}
            usdt_dict = {d[0]:d[1].get(k,0)*p.get(d[0],0)+usdt_dict.get(d[0],0) for d in b}
            coin_dict[k] = list(map(lambda x: [x[0],x[1].get(k,0)], b))
        coin_dict.update({"USDT-equivalent":[[k,v] for k,v in usdt_dict.items()]})
        self.finish(json.dumps(coin_dict))

class ding_info(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        if self.get_argument("method", None):
            qry = self.get_argument("method")
            json_obj={} if qry=="new" else self.db_client.query("ding",{})
            self.render("ding.html", user=self.user, title = "DINGDING",data = json_obj,edit=None)
        else:
            qry = self.get_argument("name")
            json_obj= self.db_client.query_one("ding",{"name":qry})
            self.render("ding.html", user=self.user, title = "DINGDING",data = {},edit=json_obj)
    
    @tornado.gen.coroutine
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
        self.redirect("/panel/ding?method=all")


handlers = [
    (r"/deploy/assignment/([0-9]+)", assignment),
    (r"/panel/server", server),
    (r"/panel/account", account), 
    (r"/panel/ding", ding_info)
]