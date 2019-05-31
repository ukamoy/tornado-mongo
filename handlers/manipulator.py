import tornado.web
from handlers import BaseHandler
import os,json,traceback,re


class mainipulator(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        print("conn get\n",args, self.request.__dict__["arguments"], "body:", self.request.__dict__["body_arguments"])
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
    (r"/dy", mainipulator), 
    (r"/q", public)
]