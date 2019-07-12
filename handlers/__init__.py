import tornado
from dayu.db_conn import db_client
from dayu.user import Member
from datetime import datetime

class BaseHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def initialize(self):
        self.db_client = db_client()
        
        self.pos_dict={}
        json_obj = self.db_client.query("strategy",{})
        for stg in json_obj:
            for sym, pos in stg["tradePos"].items():
                self.pos_dict.update({f"{stg['alias']}-{sym}":pos})
            
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
        self.user = {
            "name": db.get('name', ""), 
            "group":db.get("group", ""),
            "email" : db.get('email', ""),
            "brief" : db.get('brief', ""),
            "strategy_count" : db.get('strategy_count', 0),
            "avatar" : db.get('avatar', ""),
            "avatar_large" : db.get('avatar_large', ""),
            # "messages" : da.unread_messages(db.get('uid', ""),
            "verified" : db.get('verified', ""),
            "contacter" : db.get('contacter', ""),
            }
        print(f"{datetime.now().strftime('%y%m%d %H:%M:%S')}: {self.user['name']},{self.request.remote_ip},{self.request.uri}")
        return self.user