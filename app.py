import tornado.ioloop
import tornado.web
from tornado.options import define, options, parse_command_line
import os
import urls
from handlers.query import rotate_query

options.log_file_prefix = os.path.join(os.path.dirname(__file__), "logs/tornado.log")
options.logging = "debug"
options.log_rotate_mode = "time"
options.log_rotate_when = "D"
options.log_to_stderr = True
# options.log_file_num_backups = 5
settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    'template_path':os.path.join(os.path.dirname(__file__), "templates"),
    "login_url":"/",
    "debug":True
}

application = tornado.web.Application(urls.handlers, **settings)

if __name__ == "__main__":
    application.listen(9999)
    parse_command_line()
    x=rotate_query()
    tornado.ioloop.PeriodicCallback(x.prepare,100000).start()
    tornado.ioloop.IOLoop.current().start()