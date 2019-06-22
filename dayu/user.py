import re
import time
import hashlib
import urllib
import datetime
import smtplib
import json
from config import HOSTNAME
from dayu.db_conn import db_client

# import Mail
from dayu import regex
from dayu import constant
from dayu import exception 

class Member:
    """A wrapper.
    set_name() takes a string as argument. ValueError exception raised if the 
    string's boolean value if False. PatternMatchError exception is raised 
    if the string did not match the regex pattern. AuthError exception is 
    raised if the name was taken.
    """
    def __init__(self, entity=None):
        self._model = {
            'name': None,
            'email': None,
            'pwd': None, 
            'auth': None,
            'date': datetime.datetime.utcnow(),
            'avatar': None,
            'avatar_large': None,
            'brief': None,
            'like': [],
            'verified': False,
            'contacter':[],
            "strategy_count": []
        }
        
        if entity and isinstance(entity, dict):
            self._model = entity

        self.db_client = db_client()

    # Is is NECESSARY ???????
    def __getitem__(self, item):
        try:
            return self._model[item]
        except KeyError:
            return None

    @property 
    def name(self):
        return self._model['name']

    @property 
    def email(self):
        return self._model['email']

    @property 
    def brief(self):
        return self._model['brief']

    @property 
    def avatar_large(self):
        return self._model['avatar_large']

    @property 
    def avatar(self):
        return self._model['avatar']

    @property
    def auth(self):
        return self._model['auth']

    @property 
    def secret_key(self):
        if self._model.has_key("secret_key"):
            return self._model['secret_key']
        else:
            return None
        
    @property
    def verified(self):
        return self._model['verified'] # True or False

    @property 
    def pack(self):
        return self._model

    # Required Properties
    def set_name(self, _name):
        self._model['uid'] = self.db_client.count("user") + 1
        if not _name:
            raise exception.NameError
        elif re.match(regex.UNAME, _name):
            if self.db_client.query_one("user",{"name": _name}):
                raise exception.DupKeyError()
            else:
                self._model['name'] = _name
                self._model['name_safe'] = _name.lower()
                self._set_auth()
        else:
            raise exception.PatternMatchError()

    def add_contacter(self, _uid):
        if isinstance(_uid, int):
            if _uid in self._model['contacter']:
                self._model['contacter'].remove(_uid)
            self._model['contacter'].reverse()
            self._model['contacter'].append(int(_uid))
            self._model['contacter'].reverse()


    def set_password(self, _pwd):
        # _pwd is inscure. 
        # If _pwd is not string, TypeError (from method _encrypt_password)
        # raised.
        self._model['pwd'] = self._encrypt_password(_pwd)
        self._set_auth()

    def set_brief(self, _brief):
        self._model['brief'] = _brief

    def set_email(self, _email):
        # check
        if _email is None:
            raise ValueError
        elif re.match(regex.EMAIL, _email.lower()):
            if self.db_client.query_one("user",{"email": _email.lower()}):
                raise exception.DupKeyError()
            else:
                self._model['email'] = _email.lower() 
                self._model['verified'] = False # new email need be verified
        else:
            raise exception.PatternMatchError()

    def like(self, article):
        if int(article) not in self._model['like']:
            self._model['like'].append(int(article))
        else:
            self._model['like'].remove(int(article))
       

    def check_password(self, _pwd):
        #
        # Given a raw password, compare the generated hashed password 
        # and self._model['pwd']
        #
        try:
            if self._encrypt_password(_pwd) == self._model['pwd']:
                return True
            else:
                return False
        except TypeError:
            return False


    def set_secret_key(self, _key):
        self._model['secret_key'] = _key

    def gravatar(self, email, size=64):
        gravatar_url = ("http://www.gravatar.com/avatar/%s" % 
                        hashlib.md5(email.encode("utf-8")).hexdigest() + "?d=retro&")
        gravatar_url += urllib.parse.urlencode({'s':str(size)})
        return gravatar_url

    def verify(self):
        pass
        # netloc = urllib.parse.urlsplit(HOSTNAME).netloc
        # URL = "%s/verify?" % (HOSTNAME,) + urllib.parse.urlencode(
        #                         {"key":self._model['secret_key']})
        # SUBJECT = "[%s]邮件验证" % netloc
        # CONTENT = '''
        # <p>感谢您在 %s 注册, 点击下面的链接或将其复制到浏览器地址栏中打开进行最后的验证</p>
        # <a href="%s">%s</a>
        # ''' % (netloc, URL, URL)
        # mail = Mail(Subject=SUBJECT, To=self._model['email'], Body=CONTENT)
        # mail.Send()

    def getverified(self):
        self._model['verified'] = True

    def _encrypt_password(self, _pwd):
        # Unified password encryption algorithm
        return hashlib.sha256(_pwd.encode('utf-8')).hexdigest()

    def _set_auth(self):
        if self._model['name'] and self._model['pwd']:
            self._model['auth'] = hashlib.sha256((self._model['name'] + 
                                  self._model['pwd']).encode('utf-8')).hexdigest()

    def reload(self, _name, _pwd):
        """
        Take username and password as argument. Position matters.
        ValueError exception is raised when username's boolean value is False.
        If password is not match, AuthError exception is raised.
        More about AuthError exception see  'vanellope/exception.py'.
        """
        # Use (name, pwd) pair or auth cookie to reload
        if not _name:
            raise exception.NameError
        elif not _pwd:
            raise exception.AuthError()
        else:
            entity = self.db_client.query_one("user",{"name": _name})
            # Pymongo return None value if not match one
            if not entity:
                print("no entity")
                raise exception.AuthError()
            elif entity['pwd'] != self._encrypt_password(_pwd):
                print("AuthError")
                raise exception.AuthError()
            else:
                print("passssssssssed",self._encrypt_password(_pwd))
                self._model = entity

    def put(self):
        self._model['avatar'] = self.gravatar(self._model['email'])
        self._model['avatar_large'] = self.gravatar(self._model['email'], size=128)
        self.db_client.save("user",self._model)