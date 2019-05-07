import tornado.ioloop
import tornado.web
from tornado.options import define,options,parse_command_line
import os,json,traceback
from dayu.performance import run, get_stg_list
from dayu.queryorder import query

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", title = "DAYU")
    def post(self):
        pass

class strategy_performance(tornado.web.RequestHandler):
    def get(self):
        # query = {"status":"2"}
        # stg_list = get_stg_list(query)
        self.render("performance.html", title = "DAYU", items={})
    def post(self):
        strategy=self.get_argument("strategy_name")
        db_query = {"strategy":strategy,"status":"2"}
        try:
            result = run(db_query)
        except:
            result = "STARTEGY NAME ERROR"
        if result:
            self.render("performance.html", title = strategy, items = result)
        else:
            self.render("performance.html", title = "error", items = {})

class query_order(tornado.web.RequestHandler):
    def get(self):
        self.render("query.html", title = "FIND ORDERS",item = None)
    def post(self):
        ac=self.get_argument("ac_name")
        symbol=self.get_argument("symbol")
        oid=self.get_argument("oid")
        try:
            result = query(ac, symbol, oid)
        except:
            pass
        self.render("query.html", title = "FIND ORDERS", item = "ERROR")

class deploy(tornado.web.RequestHandler):
    def get(self):
        self.render("deploy.html", title = "DEPLOYMENT", item = "byebye")
    def post(self):
        self.render("deploy.html", title = "DEPLOYMENT", item = "ERROR")

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'template_path':os.path.join(os.path.dirname(__file__), "templates")
}

application = tornado.web.Application([
    (r"/", MainHandler), 
    (r"/deploy", deploy),
    (r"/query_order", query_order),
    (r"/strategy_performance", strategy_performance),
],**settings)

if __name__ == "__main__":
    application.listen(9999)
    tornado.ioloop.IOLoop.instance().start()