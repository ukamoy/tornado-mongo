from datetime import datetime, timezone, timedelta
from bson.objectid import ObjectId
from fabric import Connection
from config import server_credential, dingding_token, docker_conf
import json
import requests
from dayu.deployer import PortainerDeployer, ServerDeployer

def server_conn(server_ip):
    return Connection(f"dayu@{server_ip}", connect_kwargs = {"password":server_credential})

def get_server(server_name):
    # 连接到portainer: {HOST}
    deployer = PortainerDeployer(
        docker_conf["host"], 
        docker_conf["user"],
        docker_conf["pwd"]
    )

    # 连接到{SERVER}
    server = deployer.getServerByName(server_name)
    return server

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

def dingding(title, msg):
    url = f'https://oapi.dingtalk.com/robot/send'
    HEADERS={"Content-Type" : "application/json;charset=utf-8"}
    params = {"access_token" : dingding_token}
    # String_textMsg={"msgtype" : "text", "text" : {"content":'testtest'}}

    String_textMsg={
        "msgtype" : "markdown", 
        "markdown": {
                "title": title,
                "text": msg,
        }
    }

    String_textMsg = json.dumps(String_textMsg)

    res = requests.post(url, data = String_textMsg, headers = HEADERS, params = params)
    print(res, res.text)
    """
    {"errmsg":"ok","errcode":0}
    {"errmsg":"send too fast","errcode":130101}
    {"errmsg":"缺少参数 access_token","errcode":40035}
    """