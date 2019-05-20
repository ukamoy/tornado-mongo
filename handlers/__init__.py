import tornado.web
from dayu.util.db_conn import db_client
from dayu.util.user import Member
from datetime import datetime

class BaseHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.db_client = db_client()
        
        json_obj = self.db_client.query("account",{})
        ac_list = list(set(map(lambda x: x["name"],json_obj)))
        self.account_list = sorted(ac_list)

    def get_current_user(self):
        # For read only
        member = self.db_client.query_one("user", {"auth": self.get_cookie('auth')})
        if member:
            return self._member_db_map(member)
        else:
            return {}
        print()

    def get_user(self, uid=None, name=None):
        print(uid,name)
        if uid:
            return self._member_db_map(self.db_client.query_one("user",{"uid":int(uid)}))
        elif name:
            return self._member_db_map(self.db_client.query_one("user",{"name": name}))
        else: 
            return {}

    def current_user_entity(self):
        # For write
        return Member(self.db_client.query_one("user",{"auth": self.get_cookie('auth')}))

    def user_entity(self, uid=None, name=None):
        if uid:
            return Member(self.db_client.query_one("user",{"uid":int(uid)}))
        elif name:
            return Member(self.db_client.query_one("user",{"name": name}))

    def member(self, uid):
        return self._member_db_map(self.db_client.query_one("user",{"uid": int(uid)}))
        
    def is_ajax(self):
        return "X-Requested-With" in self.request.headers and \
            self.request.headers['X-Requested-With'] == "XMLHttpRequest"

    def _member_db_map(self, db):
        # The returned dict object supply a uniform database access interface 
        try:
            print(f"{datetime.now().strftime('%y%m%d %H:%M:%S')}: {db['name']}")
            return dict(
                uid = db['uid'],
                name = db['name'],
                email = db['email'],
                waitlist = db['waitlist'],            
                brief = db['brief'],
                like = db['like'],
                avatar = db['avatar'],
                avatar_large = db['avatar_large'],
                # messages = da.unread_messages(db['uid']),
                verified = db['verified'],
                contacter = db['contacter'],
                group = db['group']
            )
        except TypeError:
            return {}