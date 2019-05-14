import tornado.ioloop
import tornado.web
from tornado.options import define,options,parse_command_line
import os,json,traceback,re
from datetime import datetime
from dayu.performance import run, get_stg_list
from dayu.queryorder import query
from handlers import BaseHandler
from dayu.util.user import Member
from dayu.util.db_conn import db_client
from bson.objectid import ObjectId

def mongo_obj(id_list):
    ids = []
    for id_ in id_list:
        ids.append(ObjectId(id_))
    return ids

def prepared_data():
    ac_list = ["meetone1","meetone2","fxdayu12"]
    type_list = ["WAVE","TREND","PATTERN"]
    return ac_list, type_list

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

class deploy(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        if not current_user["group"] == "zeus":
            return self.redirect("/dashboard")

        json_obj = self.db_client.query("tasks",{},[('_id', -1)])
        self.render("deploy.html", title = "DEPLOYMENT", data = json_obj)
    
    def post(self):
        print("deploy post")

class dashboard(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        qry = {"Author":current_user["name"]}
        json_obj = self.db_client.query("strategy",qry)
        self.render("dashboard.html", title = "DASHBOARD", data = json_obj)

class new_strategy(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        ac_list, type_list = prepared_data()
        self.render("strategy.html", title = "New Strategy", data = {}, account = ac_list, stg_type = type_list)
    
    def post(self):
        current_user = self.get_current_user()
        post_values = ['strategy_class_name','strategy_type','symbols','trade_symbols',
        'strategy_git_folder','account_name']
        args = {}
        for v in post_values:
            args[v] = self.get_argument(v, None)

        stg_set = self.get_argument('strategy_setting')
        args["strategy_setting"] = json.loads(stg_set) if stg_set else {}

        if self.get_argument("_id", None):
            flt={"_id":ObjectId(self.get_argument("_id"))}
            args["updatedate"] = datetime.now().strftime("%Y%m%d")
            self.db_client.update_one("strategy", flt, args)
        else:
            args["Author"] = current_user["name"]
            args["createdate"] = datetime.now().strftime("%Y%m%d")
            args["status"] = "idle"
            self.db_client.insert_one("strategy", args)
        self.redirect("/dashboard")

class edit_strategy(BaseHandler):
    @tornado.web.authenticated
    def get(self,*args,**kwargs):
        stg = self.db_client.query_one("strategy",{"_id":ObjectId(args[0])})
        ac_list, type_list = prepared_data()
        self.render("strategy.html", title = "Edit Strategy", data = stg, account = ac_list, stg_type = type_list)

class waitlist(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        qry = {"name":current_user["name"]}
        r = self.db_client.query_one("user",qry)
        if r:
            qry = {"_id":{"$in":mongo_obj(r["waitlist"])}}
            json_obj = self.db_client.query("strategy",qry)
        else:
            json_obj = {}
        self.render("waitlist.html", title = "waitlist",data = json_obj)

    def post(self):
        current_user = self.get_current_user()
        flt = {"name":current_user["name"]}
        r = self.db_client.query_one("user",flt)
        waitlist = []
        if r:
            waitlist = r["waitlist"]
        if self.get_argument('delete',None):
            tmp = self.get_argument('delete')
            waitlist.remove(self.get_argument('delete'))
        elif self.get_argument('strategy_ids', None):
            tmp = json.loads(self.get_argument('strategy_ids'))
            waitlist += tmp
        qry= {"waitlist":list(set(waitlist))}
        self.db_client.update_one("user",flt, qry)
        self.redirect("/dashboard")

class task_sheet(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = self.get_current_user()
        qry = {"Author":current_user["name"]}
        json_obj = self.db_client.query("tasks",qry)
        ids = mongo_obj(json_obj[0]["strategy_ids"])
        pp = self.db_client.query("strategy",{"_id":{"$in":ids}})
        self.render("task_sheet.html", title = "Task List", data = json_obj)

    def post(self):
        current_user = self.get_current_user()
        task_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        args = {}
        args["task_id"] = task_id 
        args["Author"] = current_user["name"]
        args["status"] = "submitted"
        args["strategy_ids"] = json.loads(self.get_argument('strategy_ids'))
        
        self.db_client.insert_one("tasks", args)
        self.db_client.update_one("user",{"name":current_user["name"]},{"waitlist":[]})
        self.redirect("/dashboard/task_sheet")

#---------------------------------------------------------------------

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'template_path':os.path.join(os.path.dirname(__file__), "templates"),
    "login_url":"/"
}

application = tornado.web.Application([
    (r"/", MainHandler), 
    (r"/dashboard", dashboard), 
    (r"/dashboard/new_strategy", new_strategy), 
    (r"/dashboard/edit_strategy/([a-zA-Z0-9]+)", edit_strategy), 
    (r"/dashboard/waitlist", waitlist), 
    (r"/dashboard/task_sheet", task_sheet), 
    (r"/deploy", deploy),
    (r"/query_order", query_order),
    (r"/strategy_performance", strategy_performance),
],**settings)

if __name__ == "__main__":
    application.listen(9999)
    tornado.ioloop.IOLoop.instance().start()