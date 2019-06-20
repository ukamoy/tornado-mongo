from handlers import BaseHandler
from dayu.user import Member

class home(BaseHandler):
    def get(self):
        current_user = self.get_current_user()
        if current_user:
            self.redirect("/dashboard")
        else:
            self.render("index.html", user = None, title = "DAYU SYS", msg = None)
    
    def post(self):
        args = {
            "name":self.get_argument("name",None),
            "pwd":self.get_argument("pwd",None),
            "remember":self.get_argument("remember", 1),
        }

        try:
            member = Member()
            member.reload(args['name'], args['pwd'])
            self.clear_all_cookies()
            self.set_cookie(name = "auth", 
                            value = member.auth,
                            expires_days = args["remember"])
            self.redirect("/dashboard")
        except:
            self.render("index.html", user=None, title = "DAYU SYS", msg = f"username or password not match")
class logout(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect("/dashboard")
class user(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect("/dashboard")
handlers = [
    (r"/", home),
    (r"/logout", logout),
    (r"/user", user)
]