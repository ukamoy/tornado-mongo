import tornado.web
from handlers import BaseHandler
from dayu.util import server_conn, get_server, filter_name, dingding
from dayu.exchange import OKEX
from config import working_path
import re
import os
import json
from time import sleep,time
from datetime import datetime
from tornado.concurrent import run_on_executor
import logging

IMAGE = "xingehub/vnpy_fxdayu:latest"
class test(BaseHandler):
    #@tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self,*args, **kwargs):
        logging.info(f"{self.request.arguments},{args}")
        x=self.get_argument("test")
        yield self.awake(x)
    @run_on_executor
    def awake(self,var):
        sleep(8)
        print("sleep 8",time())

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
                                self.db_client.update_one("strategy",{"name":stg_name},{"server":"idle"})
                                self.db_client.insert_one("operation",{"name":stg_name,"op":0,"timestamp":now})
                                r=self.archive(server, stg_name, path)
                                res=True
                            else:
                                return self.finish(json.dumps({"error":"operation halt failed"}))
                        else:
                            self.db_client.update_one("strategy",{"name":stg_name},{"server":"idle"})
                            self.db_client.insert_one("operation",{"name":stg_name,"op":0,"timestamp":now})
                            self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"status":0})
                            return self.finish(json.dumps({"error":"container not running, you can delete it"}))
                    else:
                        self.db_client.update_one("strategy",{"name":stg_name},{"server":"idle"})
                        self.db_client.insert_one("operation",{"name":stg_name,"op":0,"timestamp":now})
                        self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"status":-1})
                        return self.finish(json.dumps({"error":"container not exists"}))
                elif method == "delete":
                    if container:
                        if container.status=="running":
                            return self.finish(json.dumps({"error":"you should halt container in advance"}))
                        else:
                            r = server.remove(stg_name)
                            self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"status":-1})
                            self.db_client.update_one("strategy",{"name":stg_name},{"server":"idle"})
                            self.db_client.insert_one("operation",{"name":stg_name,"op":0,"timestamp":now})
                    else:
                        self.db_client.update_one("strategy",{"name":stg_name},{"server":"idle"})
                        self.db_client.insert_one("operation",{"name":stg_name,"op":0,"timestamp":now})
                        self.db_client.update_one("tasks",{"strategy":stg_name,"task_id":task_id},{"status":-1})
                        
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
                        self.db_client.update_one("strategy",{"name":stg_name},{"server":server_name})
                        self.db_client.insert_one("operation",{"name":stg_name,"op":1,"timestamp":now})

                elif method == "archive":
                    res = self.archive(server, stg_name, path)
            else:
                return self.finish(json.dumps({"error":"params not exists"}))
        else:
            if method == "archive":
                return self.finish(json.dumps({"result":f"{stg_name}-latest.tar"}))
            return self.finish(json.dumps({"error":"server not exists"}))
        dingding("OPERATOR", f"* OPERATION {method} for {stg_name}: {res}")
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
        if not self.user["group"] == "zeus":
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
        logging.info(f"mainipulator get,{self.request.arguments},{args}, body:{self.request.body_arguments}")
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
        elif self.get_argument("checkPos", None):
            json_obj = self.db_client.query_one("strategy",{"name":self.get_argument("checkPos")})
            pos_dict = {}
            for sym, pos in json_obj["tradePos"].items():
                if pos[0]:
                    pos_dict.update({f"{sym}_LONG":pos[0]})
                if pos[1]:
                    pos_dict.update({f"{sym}_SHORT":pos[1]})
            self.finish(pos_dict)
        elif self.get_argument("checkPwd", None):
            user=self.current_user_entity()
            msg=False
            if user.check_password(self.get_argument("checkPwd")):
                msg=True
            self.finish(json.dumps(msg))
        elif self.get_argument("getAccount", None):
            json_obj = self.db_client.query("exchange",{})
            ac_dict = {}
            for ex in json_obj:
                ac_dict.update({ex["name"]:[ex["keys"],ex["symbols"]]})
            self.finish(ac_dict)
        elif self.get_argument("deleteStrategy",None):
            name = self.get_argument("deleteStrategy",None)
            self.db_client.delete_one("strategy",{"name":name})

class clear_pos(BaseHandler):
    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        current_user = self.get_current_user()
        logging.info(f"clearpos post,{self.request.arguments},{args}, body:{self.request.body_arguments}")
        sym,ac,direction = self.get_argument("symbol").split("_")
        qty = self.get_argument("qty")
        stg = filter_name(self.get_argument("strategy"))
        contract_map, contract_reverse = OKEX.query_futures_instruments()
        instrument = contract_map[sym.split(":")[0]]

        account_info = self.db_client.query_one("account",{"name":ac})
        gateway = OKEX(account_info)
        open_orders = gateway.query_futures_orders(instrument,"6")
        print(open_orders)
        if open_orders.get("result",False):
            orders = open_orders["order_info"]
            need_to_cancel = list(map(lambda x:x["client_oid"] if x["client_oid"].split("FUTU")[0]==stg else None, open_orders["order_info"]))
        need_to_cancel=list(set(need_to_cancel))
        len_cancel_order = len(need_to_cancel)
        print(need_to_cancel)
        for oid in list(need_to_cancel):
            if not oid:
                need_to_cancel.remove(None)
                continue

            r = gateway.cancel_futures_order(instrument, oid)
            print(r)
            if r.get("result", False):
                need_to_cancel.remove(oid)
        if len(need_to_cancel)>0:
            dingding("INSTANCE CONTROL",f"{stg}, error in cancelling orders")
        else:
            order_type = "3" if direction == "LONG" else "4"
            futures_price = OKEX.query_futures_price(instrument)
            price = f"{futures_price/1.02:0.3f}" if direction == "LONG" else f"{futures_price*1.02:0.3f}"
            oid = f"{stg}FUTUDSB{datetime.now().strftime('%y%m%d%H%M')}"
            r = gateway.send_futures_order(oid, order_type, instrument, price, qty)
            if r.get("result",False):
                dingding("INSTANCE CONTROL",f"> CLEAR POSITION: {stg}\n\n {current_user['name']} cancelled {len_cancel_order} open orders and closed postion")
            else:
                dingding("INSTANCE CONTROL",f"{stg}, error in close position:{r}")

class public(BaseHandler):
    @tornado.gen.coroutine
    def prepare(self):
        member = self.db_client.query_one("user", {"auth": self.get_cookie('auth')})
        logging.info(f"public prepare: {member.get('name','not member')},{self.request.arguments}, body:{self.request.body_arguments}")

        if not member:
            raise tornado.web.HTTPError(403)

    @tornado.gen.coroutine
    def get(self):
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

handlers = [
    (r"/operator", operator),
    (r"/operator/clear_pos", clear_pos), 
    (r"/dy", mainipulator), 
    (r"/q", public),
    (r"/old_operator", old_operator),
    (r"/test", test)
]
