from handlers import BaseHandler
from dayu.user import Member
import re
import hashlib
import urllib
#import urllib.urlparse
import datetime
import smtplib
import string
import random
import json
import config
import tornado

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
                            expires_days = int(args["remember"]))
            self.redirect("/dashboard")
        except Exception as e:
            print("login error",e)
            self.render("index.html", user=None, title = "DAYU SYS", msg = f"username or password not match")
class logout(BaseHandler):
    def get(self):
        referer = self.request.headers['Referer']
        self.clear_all_cookies()
        self.redirect(referer)

class user(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("user.html", user=self.user, title = f"User Panel: {self.user['name']}",user_info = self.get_current_user(),errors=None,key=None)

class RegisterHandler(BaseHandler):
    def get(self):
        current_user = self.get_current_user()
        self.render("register.html", 
                    title = '注册',
                    errors = None,
                    master = current_user)

    #@tornado.web.asynchronous
    def post(self):
        errors = [] # errors message container
        member = Member()
        post_values = ['name','pwd','cpwd','email']
        args = {}
        for v in post_values:
            # Get nessary argument
            # Use None as default if argument is not supplied
            args[v] = self.get_argument(v, None)

        # Set user name
        try:
            member.set_name(args['name'])
        except exception.NameError:
            errors.append(u"请填写用户名")
        except exception.DupKeyError:
            errors.append(u"用户名已经被使用")
        except exception.PatternMatchError:
            errors.append(u"你填写的用户名中有不被支持的字符")

        # Set user password
        if args['pwd'] != args['cpwd']:
            errors.append(u"两次输入的密码不一致")
        elif args['pwd'] is None and args['cpwd'] is None:
            errors.append(u"请填写密码")
        else:
            member.set_password(args['pwd'])

        # set user email
        try:
            member.set_email(args['email'])
        except ValueError:
            errors.append(u"请填写邮箱")
        except exception.DupKeyError:
            errors.append(u"邮箱已经被使用")
        except exception.PatternMatchError:
            errors.append(u"邮件地址格式不正确")

        if errors:
            self.render("register.html", 
                        title = u"注册", 
                        errors = errors,    
                        master = None)
        else:
            member.set_secret_key(randomwords(20))
            member.verify()
            member.put()
            self.set_cookie(name="auth", 
                            value=member.auth, 
                            expires_days = 365)
            self.redirect('/')



class VerifyHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        #
        # Database member entity's "verified" tag is initially "False"
        # until this method is called.
        #
        # TODO: complete notification message display
        #
        errors = []
        secret_key = self.get_argument("key", None)
        
        current_user = self.current_user_entity()
        if not current_user.verified:
            # Verify secret key and set "verified" tag to "True"
            if secret_key == current_user.secret_key:
                current_user.getverified()
                current_user.put()
                self.redirect("/") # everything fine
            else:
                self.send_error(403) # url insecure
        else:
            self.redirect("/") # email has been verified
        self.finish()


class ForgetHandler(BaseHandler):
    def get(self):
        self.render("forget.html", 
            title="Login", 
            errors=None, 
            master=None)

    def post(self):
        errors = []
        template = "forget.html"
        post_values = ['name','email']
        args = {}
        for v in post_values:
            # Get nessary argument
            # Use None as default if argument is not supplied
            args[v] = self.get_argument(v, None)

        if args['name'] is None:
            errors.append(u"请填写用户名")
        elif args['email'] is None:
            errors.append(u"请填写邮箱")
        else:
            member = da.get_member_by_name(args['name'])
            if not member:
                errors.append(u"这个用户不存在")
            elif args['email'].lower() != member['email']:
                errors.append(u"不是用户注册时使用的邮箱")
            elif not member.verified:
                errors.append(u"此邮箱未通过验证，不能用于找回密码")
            else:
                member.set_secret_key(randomwords(20))
                member.put()
                self.send_email(member['email'], member.secret_key)

        if len(errors) > 0:
            self.render("forget.html", 
                        title = "找回密码", 
                        master = None, 
                        errors = errors)
        else:
            self.redirect("/")

    def send_email(self, email, key):
        netloc = urlparse.urlsplit(config.HOSTNAME).netloc
        URL = "%s/password?" % (config.HOSTNAME,)+urllib.urlencode({"key":key})
        SUBJECT = "[%s]找回密码" % netloc
        CONTENT = '''
        <p>点击下面的链接或将其复制到浏览器地址栏中打开来设密重码</p>
        <a href="%s">%s</a>
        ''' % (URL, URL)
        mail = Mail(Subject=SUBJECT, To=email, Body=CONTENT)
        mail.Send()


class PasswordResetHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):        
        master = self.current_user_entity()
        try:
            master.set_password(self.get_argument("new_pwd"))
            master.put()
            self.clear_all_cookies()
            self.set_cookie("auth", master.auth)
            msg=True
        except Exception as e:
            msg=False
        self.finish(json.dumps(msg))

class PasswordHandler(BaseHandler):
    def get(self):
        secret_key = self.get_argument("key", None)
        member = db.member.find_one({"secret_key": secret_key})
        if member:
            self.render("password.html", 
                        title="更改密码", 
                        errors=None, 
                        master=None, 
                        key=secret_key)
        else:
            self.send_error(404)
            self.finish()

    def post(self):
        #
        # Use secret_key to get the user who send change password request.
        # Replace old password with the new one.
        # update everything related to the password, 
        # like auth string, secure cookie , etc.
        #
        errors = []
        post_values = ['pwd','cpwd', 'key']
        args = {}
        for v in post_values:
            # Get nessary argument
            # Use None as default if argument is not supplied
            args[v] = self.get_argument(v, None)
    
        member = db.member.find_one({"secret_key": args['key']})
        master = self.current_user_entity()
        if args['pwd'] == args['cpwd']:
            try:
                master.set_password(args['pwd'])
                master.put()
                self.clear_all_cookies()
                self.set_cookie("auth", master.auth)
            except TypeError: # this try/except has no "else" statement
                errors.append(u"密码不能为空")
        else:
            errors.append(u"新密码两次输入不一致")
        if len(errors) > 0:
            self.render("password.html", 
                        title="更改密码", 
                        errors=errors, 
                        master=False, 
                        key=args['key'])
        else:
            self.redirect("/home")


def randomwords(length):
    random.seed()
    return ''.join(random.choice(string.lowercase 
                + string.uppercase + string.digits) for i in range(length))


handlers = [
    (r"/", home),
    (r"/logout", logout),
    (r"/user", user),
    (r"/reset", PasswordResetHandler),
    (r"/password", PasswordHandler),
    (r"/register", RegisterHandler),
    (r"/forget", ForgetHandler),
    (r"/verify", VerifyHandler),
]