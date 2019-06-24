import tornado.ioloop
import tornado.web
# from tornado.options import define,options,parse_command_line
import os
import urls
from handlers.query import rotate_query

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'template_path':os.path.join(os.path.dirname(__file__), "templates"),
    "login_url":"/",
}

application = tornado.web.Application(urls.handlers,**settings)

if __name__ == "__main__":
    application.listen(9999)
    x=rotate_query()
    tornado.ioloop.PeriodicCallback(x.prepare,100000).start()
    tornado.ioloop.IOLoop.current().start()