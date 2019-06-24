import tornado.web
from handlers import BaseHandler
from handlers.query import generateSignature, query_price, okex_sign, arb_symbol, OKEX_REST_HOST
from dayu.util import server_conn, get_server, filter_name, dingding
from config import working_path
import re
import os
import json
import requests
from urllib.parse import urlencode
from time import sleep,time
from datetime import datetime
from tornado.concurrent import run_on_executor

IMAGE = "daocloud.io/xingetouzi/vnpy-fxdayu:v1.1.20"
class test(BaseHandler):
    #@tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self,*args, **kwargs):
        print(self.request.arguments,args)
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
class clear_pos(BaseHandler):
    @tornado.gen.coroutine
    def post(self,*args,**kwargs):
        current_user = self.get_current_user()
        print("clearpos post",args, self.request.arguments, "body:", self.request.body_arguments)
        d=self.get_argument("symbol").split("_")
        qty=self.get_argument("qty")
        stg=filter_name(self.get_argument("strategy"))
        sym,ac,direction = d
        instrument = arb_symbol(sym.split(":")[0])

        account_info = self.db_client.query_one("account",{"name":ac})
        open_orders = self.query_open_orders(account_info,instrument)  
        r=open_orders.result()
        if r.get("result",False):
            orders = r["order_info"]
            need_to_cancel = list(map(lambda x:x["client_oid"] if x["client_oid"].split("FUTU")[0]==stg else None, r["order_info"]))
        len_cancel_order = len(need_to_cancel)
        oids = self.cancel_order(account_info, instrument, (list(set(need_to_cancel))))
        if len(oids.result())>0:
            dingding("INSTANCE CONTROL",f"{stg}, error in cancelling orders")
        else:
            r = self.close_position(account_info, stg, instrument, direction, qty)
            print(r)
            if r.get("result",False):
                dingding("INSTANCE CONTROL",f"> CLEAR POSITION: {stg}\n\n {current_user['name']} cancelled {len_cancel_order} open orders and closed postion")
            else:
                dingding("INSTANCE CONTROL",f"{stg}, error in close position:{r}")

    def close_position(self, account_info, strategy, instrument, direction, qty):
        data={
            "client_oid": f"{strategy}FUTUDSB{datetime.now().strftime('%y%m%d%H%M')}",
            "instrument_id":instrument,
            "size":str(int(qty)),
            "match_price":"0",
            "order_type":"0",
            "leverage":str(account_info["future_leverage"])
        }
        if direction=="LONG":
            data.update({"type":"3", "price":f"{query_price(instrument)/1.02:0.3f}"})
        else:
            data.update({"type":"4", "price":f"{query_price(instrument)*1.02:0.3f}"})
        path = f'/api/futures/v3/order'
        path = f"{path}?{urlencode(data)}"
        
        timestamp = f"{datetime.utcnow().isoformat()[:-3]}Z"
        data=json.dumps(data)
        msg = f"{timestamp}POST{path}{data}"
        signature = generateSignature(msg, account_info["secretkey"])
        headers = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': account_info["apikey"],
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': account_info["passphrase"]
        }
        #headers = okex_sign(account_info,"POST",path,data)
        print(headers,path)
        url = f"{OKEX_REST_HOST}{path}"
        r = requests.post(url, headers = headers, data=data, timeout =10)
        return r.json()
    @tornado.gen.coroutine
    def cancel_order(self, account_info, symbol, oids):
        for oid in list(oids):
            if oid:
                timestamp = f"{datetime.utcnow().isoformat()[:-3]}Z"
                path = f'/api/futures/v3/cancel_order/{symbol}/{oid}'
                msg = f"{timestamp}POST{path}"
                signature = generateSignature(msg, account_info["secretkey"])
                headers = {
                    'Content-Type': 'application/json',
                    'OK-ACCESS-KEY': account_info["apikey"],
                    'OK-ACCESS-SIGN': signature,
                    'OK-ACCESS-TIMESTAMP': timestamp,
                    'OK-ACCESS-PASSPHRASE': account_info["passphrase"]
                }
                url = f"{OKEX_REST_HOST}{path}"
                r = requests.post(url, headers = headers, timeout =10).json()
                if r.get("result",False):
                    oids.remove(oid)
            else:
                oids.remove(oid)
        return oids
    @tornado.gen.coroutine
    def query_open_orders(self, account_info, symbol):
        path = f'/api/futures/v3/orders/{symbol}'
        params={"state":"6","instrument_id":symbol,"limit":100}
        path = f"{path}?{urlencode(params)}"
        headers=okex_sign(account_info,"GET",path,params)
        url = f"{OKEX_REST_HOST}{path}"
        r = requests.get(url, headers = headers, timeout =10)
        return r.json()

class public(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        print(self.request.arguments)
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
    (r"/operator/clear_pos", clear_pos), 
    (r"/dy", mainipulator), 
    (r"/q", public),
    (r"/old_operator", old_operator),
    (r"/test", test)
]
