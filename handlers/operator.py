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
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return False
        stg_name = self.get_argument('name',None)
        method = self.get_argument('method',None)
        task_id = self.get_argument('task_id',None)

        json_obj = self.db_client.query_one("strategy",{"name":stg_name}) 
        server = get_server(json_obj['server'])
        res=False
        if server:
            container = server.get(stg_name)
            if method and stg_name:
                if method == "halt":
                    res=self.halt(server, container, stg_name)
                elif method == "launch":
                    res=self.launch(server, container, stg_name, task_id)
            else:
                raise tornado.web.HTTPError(403)
        self.finish(json.dumps(res))
            
    def launch(self, server, container, strategy, task_id):
        running = False
        if container:
            # 如果容器已经在运行, 则跳过下面一系列步骤
            if container.status == "running":
                print(f"Strategy: {strategy} already running.")
                running = True
            else:
                command = input("Strategy container already exists, do you want to proceed? [y/n]: ")
                if command == "y":
                    print(f"container status: {container.status}")
                else:
                    print("Exit.")
                    return 
        else:
            # 使用指定{IMAGE}创建策略{strategy} 
            r = server.create(
                IMAGE, # 镜像名
                strategy, # 策略名
                f"{working_path}/{task_id}/{strategy}" # 策略文件夹路径
            )
            print(r)
            assert r, "Strategy not deployed properly."

            # 获取当前策略快照并保存到本地，该快照可以供策略师确认配置
            # archive = server.archive(strategy)
            # with open(f"{strategy}-created.tar", "wb") as f:
            #     f.write(archive)
        
        if not running:
            if input("Do you want to start strategy now? [y/n]: ") != "y":
                print("Exit.")
                return True

            # 策略师确认后运行策略。
            status = server.start(strategy)
            print(status)
            assert status == "running", f"Status of {strategy} is not [running] but [{status}]" 
        return running

    def halt(self, server, container, strategy):
        while container.status == "running":
            command = input("Enter command:\ns: Stop strategy\ne: Exit\n")
            if command == "s":
                break
            elif command == "e":
                return 
            container.reload()

        # 如果容器在运行，则停止容器。
        container = server.get(strategy)
        if container.status == "running":
            r = server.stop(strategy)
            print(r)
        server.remove(strategy)
        self.db_client.update_one("strategy",{"name":strategy},{"server":"idle"})
        return True

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
        print("conn get",args, self.request.arguments, "body:", self.request.body_arguments)
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
            self.finish(self.ac_dict)
            return

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
