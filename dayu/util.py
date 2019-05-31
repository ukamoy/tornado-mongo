from datetime import datetime, timezone, timedelta
from bson.objectid import ObjectId

def mongo_obj(id_list):
    ids = []
    for id_ in id_list:
        ids.append(ObjectId(id_))
    return ids
def filter_name(name):
    alpha='abcdefghijklmnopqrstuvwxyz'
    filter_text = "0123456789" + alpha + alpha.upper()
    new_name = filter(lambda ch: ch in filter_text, name)
    return ''.join(list(new_name))[:13]
def convertDatetime(timestring):
    dt = datetime.strptime(timestring, '%Y-%m-%dT%H:%M:%S.%fZ')
    dt = dt.replace(tzinfo=timezone(timedelta()))
    local_dt = datetime.fromtimestamp(dt.timestamp())
    return local_dt