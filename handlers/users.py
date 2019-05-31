from handlers import BaseHandler
from dayu.util.user import Member

class home(BaseHandler):
    def get(self):
        current_user = self.get_current_user()
        if current_user:
            self.redirect("/dashboard")
        else:
            self.render("index.html", title = "DAYU SYS", msg=None)
    
    def post(self):
        args = {
            "name":self.get_argument("name",None),
            "pwd":self.get_argument("pwd",None)
        }

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

handlers = [
    (r"/", home)
]