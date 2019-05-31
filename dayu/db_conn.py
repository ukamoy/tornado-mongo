from config import dbURI, dbname
import pymongo

class db_client(object):

    def __init__(self):
        self.db = db=pymongo.MongoClient(dbURI)[dbname]

    def query(self, collection, qry, sort = None, projection=None):
        cur = self.db[collection].find(qry, sort=sort, projection=projection)
        return list(cur)

    def query_one(self, collection, qry):
        cur = self.db[collection].find_one(qry)
        return cur

    def insert_one(self, collection, qry):
        self.db[collection].insert_one(qry)

    def insert_many(self, collection, qry):
        self.db[collection].insert_many(qry)

    def replace_one(self, collection, flt, qry):
        self.db[collection].replace_one(flt, qry)

    def update_one(self, collection, flt, qry):
        self.db[collection].update(flt, {"$set":qry}, upsert=True)

    def update_many(self, collection, flt, qry):
        self.db[collection].update_many(flt, qry)

    def delete_one(self, collection, qry):
        self.db[collection].delete_one(qry)

    def delete_many(self, collection, qry):
        self.db[collection].delete_many(qry)

    def save(self, collection, qry):
        self.db[collection].save(qry)

    def count(self, collection, qry = {}):
        return self.db[collection].find(qry).count()