import tornado
from dayu.db_conn import db_client
from dayu.user import Member
from datetime import datetime

class BaseHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def initialize(self):
        self.db_client = db_client()
        
        self.pos_dict={}
        json_obj = self.db_client.query("pos",{})
        for pos in json_obj:
            self.pos_dict.update({pos["name"]:[pos["long"],pos["short"]]})

        json_obj2 = self.db_client.query("exchange",{})
        self.ac_dict = {}
        for ex in json_obj2:
            self.ac_dict.update({ex["name"]:[ex["keys"],ex["symbols"]]})
            
    def get_current_user(self):
        # For read only
        member = self.db_client.query_one("user", {"auth": self.get_cookie('auth')})
        if member:
            return self._member_db_map(member)
        else:
            return {}

    def get_user(self, uid=None, name=None):
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
                # waitlist = db['waitlist'],            
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