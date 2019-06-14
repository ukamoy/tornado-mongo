import tornado.web
from handlers import BaseHandler
from dayu.util import mongo_obj,server_conn, dingding
import os,json,traceback,re
from bson import ObjectId
from dayu.write_settings import update_repo, prepare_stg_files, cp_files

class deploy(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args, **kwargs):
        # current_user = self.get_current_user()
        # if not current_user["group"] == "zeus":
        #     return self.redirect("/dashboard")
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
        dingding("deploy", f"{task['Author']}'s task {method}\n\n id:{task['task_id']} ")

class assignment(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return self.redirect("/dashboard")
        task = self.db_client.query_one("tasks",{"task_id":args[0]})
        stgs = task["strategies"]
        json_obj = self.db_client.query("strategy",{"name":{"$in":stgs}}) 
        servers = self.db_client.query("server",{},[('_id', -1)])
        serv_name = list(map(lambda x: x["server_name"], servers))
        self.render("assign.html", title = "ASSIGN SERVER", data = json_obj, serv = serv_name, Author = task['Author'], task_id=args[0], status=task["status"])
    
    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        # update db for assigned strategy
        server_name = self.get_arguments('server_name')
        _ids = self.get_arguments('_id')
        for serv, _id in zip(server_name, _ids):
            self.db_client.update_one("strategy",{"_id":ObjectId(_id)},{"server":serv})
        
        # prepare strategy
        Author = self.get_argument('Author')
        task_id = self.get_argument('task_id')
        servers = self.db_client.query("server",{"server_name":{"$in":server_name}})
        for server in servers:
            c = server_conn(server["server_ip"])
            msg = cp_files(c, server["server_name"], task_id)
        self.db_client.update_one("tasks",{"task_id":task_id,"Author":Author},{"status":"assigned"})
        print("deploy", f"{Author}'s task {task_id} assigned \n\n {msg}")
        self.redirect(f"/deploy/assignment/{task_id}")

class server(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return self.redirect("/dashboard")

        json_obj = self.db_client.query("server",{},[('_id', -1)])
        self.render("server.html", title = "SERVER MGMT", data = json_obj)
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

class ding_info(BaseHandler):
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


handlers = [
    (r"/deploy/list/(all|todo|work)", deploy),
    (r"/deploy/assignment/([0-9]+)", assignment),
    (r"/deploy/server", server),
    (r"/ding", ding_info), 
]