import tornado.web
from handlers import BaseHandler
from dayu.util import server_conn, get_server, filter_name, dingding
from dayu.write_settings import update_repo, prepare_stg_files
from config import working_path
import re
import os
import json
from time import sleep
from datetime import datetime
IMAGE = "daocloud.io/xingetouzi/vnpy-fxdayu:v1.1.20"

class operator(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self,*args, **kwargs):
        stg_name = self.get_argument('name',None)
        method = self.get_argument('method',None)
        task_id = self.get_argument('task_id',None)
        path = f"{working_path}/{task_id}" # 策略文件夹路径
        server_name = self.get_argument('server',None)

        if server_name =="idle":
            if method == "archive":
                return self.finish(json.dumps({"result":f"{stg_name}-latest.tar"}))
            elif method=="delete":
                self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"status":-1})
                return self.finish(json.dumps({"result":True}))

        server = get_server(server_name)
        res=False

        if server:
            container = server.get(stg_name)
            if method and stg_name:
                now = int(datetime.now().timestamp()*1000)
                if method == "halt":
                    if container:
                        if container.status == "running":
                            status = server.stop(stg_name)
                            if status=="exited":
                                self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"status":0})
                                self.db_client.insert_one("operation",{"name":stg_name,"op":0,"timestamp":now})
                                r=self.archive(server, stg_name, path)
                                
                                res=True
                            else:
                                return self.finish(json.dumps({"error":"operation halt failed"}))
                        else:
                            return self.finish(json.dumps({"error":"container not running"}))
                    else:
                        return self.finish(json.dumps({"error":"container not exists"}))
                elif method == "delete":
                    if container:
                        if container.status=="running":
                            return self.finish(json.dumps({"error":"you should halt container in advance"}))
                        else:
                            r = server.remove(stg_name)
                            if not r:
                                res = True
                                self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"status":-1})
                    else:
                        return self.finish(json.dumps({"error":"container not exists"}))
                        
                elif method == "launch":
                    if not container:
                        r = server.create(
                            IMAGE, # 镜像名
                            stg_name, # 策略名
                            f"{path}/{stg_name}"
                        )
                        print("create container:",r)
                   
                    status = server.start(stg_name)
                    if status == "running":
                        res=True
                        self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"server":server_name,"status":1})
                        self.db_client.insert_one("operation",{"name":stg_name,"op":1,"timestamp":now})

                elif method == "archive":
                    res = self.archive(server, stg_name, path)
            else:
                return self.finish(json.dumps({"error":"params not exists"}))
        else:
            if method == "archive":
                return self.finish(json.dumps({"result":f"{stg_name}-latest.tar"}))
            return self.finish(json.dumps({"error":"server not exists"}))

        self.finish(json.dumps({"result":res}))

    def archive(self, server, strategy, path):
        archive = server.archive(strategy)
        with open(f"{path}/{strategy}-latest.tar", "wb") as f:
            f.write(archive)
        return f"{strategy}-latest.tar"

class old_operator(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self,*args, **kwargs):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return False
        stg_name = self.get_argument('name',None)
        method = self.get_argument('method',None)

        json_obj = self.db_client.query_one("strategy",{"name":stg_name}) 
        server = self.db_client.query_one("server",{"server_name":json_obj['server']}) 
        if not server:
            self.finish(json.dumps(False))
        else:
            c = server_conn(server['server_ip'])

            if method and stg_name:
                if method == "halt":
                    res=self.halt(c, stg_name)
                elif method == "launch":
                    res=self.launch(c, stg_name)
            else:
                raise tornado.web.HTTPError(403)
            self.finish(json.dumps(res))
            
    def launch(self,c, run_stg):
        sleep(5)
        #c.cd(f"/home/dayu/Documrnts/Strategy/{run_stg}")
        #c.run("nohup /home/dayu/anaconda3/bin/vnpy run terminal -m")
        return False
        
    def halt(self, c, kill_stg):
        res = c.run(f"ps -ef |grep vnpy")
        tag = res.stdout.split("\n")
        for i in list(tag):
            if not "vnpy run terminal -m" in i:
                tag.remove(i)
        pids=list(map(lambda x: re.findall(r"(\d+)",x)[0],tag))

        stgs={}
        for pid in pids:
            res = c.run(f"ls -l /proc/{pid}/cwd")
            stg = res.stdout.split("/")[-1].replace("\n","")
            p=stgs.get(stg,[])
            p.append(pid)
            stgs[stg]=p
        if stgs.get(kill_stg,None):
            c.run(f"kill -2 {min(stgs[kill_stg])}")
        else:
            return True

        sleep(5)
        now=datetime.now().strftime('%Y%m%d')
        with c.cd("/home/dayu/BACKUP/"):
            p=c.run("ls")
            if not now in p.stdout.split("\n"):
                c.run(f"mkdir {now}")
        c.run(f"mv /home/dayu/Strategy/{kill_stg} /home/dayu/BACKUP/{now}/")
        self.db_client.update_one("strategy",{"name":kill_stg},{"server":"idle"})
        with c.cd("/home/dayu/Strategy"):
            p=c.run("ls")
            if kill_stg in p.stdout.split("\n"):
                return False
            else:
                return True


class mainipulator(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self,*args,**kwargs):
        print("mainipulator get",args, self.request.arguments, "body:", self.request.body_arguments)
        if self.get_argument("checkName", None):
            qry = filter_name(self.get_argument("checkName"))
            r = self.db_client.query_one("strategy",{"alias":qry})
            msg = True if r else False
            self.finish(json.dumps(msg))
        elif self.get_argument("checkUser", None):
            qry = self.get_argument("checkUser")
            r = self.db_client.query_one("user",{"name":qry})
        elif self.get_argument("checkDing", None):
            qry = self.get_argument("checkDing")
            r = self.db_client.query_one("ding",{"name":qry})
            msg = True if r else False
            self.finish(json.dumps(msg))
        elif self.get_argument("task_id", None):
            t = self.get_argument("task_id")
            n = self.get_argument("stg_name")
            qry = {"_id":ObjectId(t)}
            r = self.db_client.query_one("tasks",qry)
            running_stg = r["running"].append(n)
            self.db_client.update_one("tasks",qry,{"running":running_stg})
            msg = True if r else False
            self.finish(json.dumps(msg))
        elif self.get_argument("getAccount", None):
            json_obj = self.db_client.query("exchange",{})
            ac_dict = {}
            for ex in json_obj:
                ac_dict.update({ex["name"]:[ex["keys"],ex["symbols"]]})
            self.finish(ac_dict)

    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        print("mainipulator post",args, self.request.arguments, "body:", self.request.body_arguments)
        if self.get_argument("change_status",None):
            n = self.get_argument("change_status")
            s = self.get_argument("status")
            self.db_client.update_one("strategy",{"name":n},{"status":int(s)})

class public(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        member = self.db_client.query_one("user", {"auth": self.get_cookie('auth')})
        if member:
            if self.get_argument("strategy", None):
                name = self.get_argument("strategy", None)
                qry = {} if name =="all" else {"name":name} 
                r = self.db_client.query("strategy",qry, projection={"_id":0})
                self.finish(json.dumps(r))
            if self.get_argument("ding", None):
                name = self.get_argument("ding", None)
                qry = {} if name =="all" else {"name":name} 
                r = self.db_client.query("ding",qry, projection={"_id":0})
                self.finish(json.dumps(r))
        else:
            raise tornado.web.HTTPError(403)


handlers = [
    (r"/operator", operator),
    (r"/dy", mainipulator), 
    (r"/q", public),
    (r"/old_operator", old_operator)
]
