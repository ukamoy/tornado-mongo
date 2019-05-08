import tornado.ioloop
import tornado.web
from tornado.options import define,options,parse_command_line
import os,json,traceback
from dayu.performance import run, get_stg_list
from dayu.queryorder import query
from handlers import BaseHandler
from dayu.util.user import Member

class MainHandler(BaseHandler):
    def get(self):
        current_user = self.get_current_user()
        if current_user:
            self.redirect("/dashboard")
        else:
            self.render("index.html", title = "DAYU SYS")

class LoginHandler(BaseHandler):
    def post(self):
        post_values = ['name','pwd']
        args = {}
        for v in post_values:
            args[v] = self.get_argument(v, None)

        try:
            # BUG: can not chain like this "member = Member().reload()"
            member = Member()
            member.reload(args['name'], args['pwd'])
            self.clear_all_cookies()
            self.set_cookie(name = "auth", 
                            value = member.auth,
                            expires_days = 15)
            self.redirect("/dashboard")
        except:
            pass

class dashboard(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("dashboard.html", title = "DASHBOARD")

class strategy_performance(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        # query = {"state":"2"}
        # stg_list = get_stg_list(query)
        self.render("performance.html", title = "DAYU", items={})
    
    def post(self):
        strategy=self.get_argument("strategy_name")
        db_query = {"strategy":strategy,"state":{"$in":["-1","2"]}}
        try:
            result = run(db_query)
        except:
            result = "STARTEGY NAME ERROR"
        if result:
            self.render("performance.html", title = strategy, items = result)
        else:
            self.render("performance.html", title = "error", items = {})

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

class deploy(tornado.web.RequestHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("deploy.html", title = "DEPLOYMENT", item = "not today")
    
    def post(self):
        self.render("deploy.html", title = "DEPLOYMENT", item = "ERROR")

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'template_path':os.path.join(os.path.dirname(__file__), "templates"),
    "login_url":"/"
}

application = tornado.web.Application([
    (r"/", MainHandler), 
    (r"/login", LoginHandler), 
    (r"/dashboard", dashboard), 
    (r"/deploy", deploy),
    (r"/query_order", query_order),
    (r"/strategy_performance", strategy_performance),
],**settings)

if __name__ == "__main__":
    application.listen(9999)
    tornado.ioloop.IOLoop.instance().start()