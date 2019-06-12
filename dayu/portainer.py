import requests
import docker
import logging
import json
import os



class PortainerAPIExcepition(Exception):

    def __init__(self, status_code, text, *args, **kwargs):
        self.status_code = status_code
        self.text = text
        super().__init__(f"status_code={status_code}, message={text}", *args, **kwargs)
    

def catch200wrap(method):
    def func(*args, **kwargs):
        resp = method(*args, **kwargs)
        return catch200(resp)
    return func


def catch200(resp):
    if resp.status_code == 200:
        return resp.json()
    else:
        raise PortainerAPIExcepition(resp.status_code, resp.text)


def catchCodeWrap(code):
    def catch(resp):
        if resp.status_code == code:
            return resp.json()
        else:
            raise PortainerAPIExcepition(resp.status_code, resp.text)

    def wrapper(method):
        def func(*args, **kwargs):
            resp = method(*args, **kwargs)
            return catch(resp)
        return func
    
    return wrapper


class PortainerAPI(object):

    def __init__(self, host, headers=None):
        self.host = host
        self.headers = headers if isinstance(headers, dict) else {}
        self.dockerClients = {}
    
    def setHeaderJWT(self, jwt):
        self.headers["Authorization"] = f"Bearer {jwt}"

    def auth(self, username, password):
        resp = PortainerAPI.req(self, 'post', "/auth", json={
            "Username": username,
            "Password": password
        })
        doc = catch200(resp)
        jwt = doc["jwt"]
        self.setHeaderJWT(jwt)
        self.authDockerClients()
        return doc

    def isAuthed(self):
        return "Authorization" in self.headers
    
    def req(self, method, api, **kwargs):
        url = self.host + api
        kwargs.setdefault("headers", {}).update(self.headers)
        resp = requests.request(method, url, **kwargs)
        return resp

    @property
    def endpoints(self):
        return Endpoints(self.host, self.headers)
    
    def registerDockerClient(self, key, client):
        assert isinstance(client, docker.DockerClient)
        self.dockerClients[key] = client
        client.api.headers.update(self.headers)

    def authDockerClients(self):
        for client in self.dockerClients.values():
            client.api.headers.update(self.headers)

class PortainerSubAPI(PortainerAPI):

    def __init__(self, host, api, headers=None):
        super().__init__(host, headers)
        self.api = api
    
    def req(self, method, api="", **kwargs):
        return super().req(method, self.api+api, **kwargs)


class Endpoints(PortainerSubAPI):

    def __init__(self, host, headers=None):
        super().__init__(host, "/endpoints", headers)
        self.clients = {}
    
    @staticmethod
    def onUpload(resp):
        if resp.status_code // 200 == 1:
            return True
        else:
            return catch200(resp)
    
    @catch200wrap
    def getAll(self):
        return self.req("get")

    @catch200wrap
    def get(self, _id):
        return self.req("get", f"/{_id}")

    @catch200wrap
    def post(self, Name, EndpointType, URL, **kwargs):
        params = {
            "Name": Name,
            "EndpointType": EndpointType,
            "URL": URL
        }
        if "params" in kwargs:
            kwargs["params"].update(params)
        return self.req("post", **kwargs)
    
    @catch200wrap
    def put(self, _id, body):
        return self.req(
            "put",
            f"/{_id}",
            json=body
        )
    
    def upload(self, _id, certificate, file):
        resp = PortainerAPI.req(
            self,
            "post",
            f"/upload/tls/{certificate}?folder={_id}",
            files={
                "file": (
                    f"{certificate}.pem",
                    file,
                    "application/octet-stream"
                )
            }
        )
        return self.onUpload(resp)

    def docker(self, _id):
        return EndpointDocker(self.host, _id, self.headers)
    
    def dockerClient(self, _id):
        if _id in self.clients:
            client = self.clients[_id]
        else:
            url = f"{self.host}/endpoints/{_id}/docker"
            client = docker.DockerClient(url)
            client.api.headers.update(self.headers)
            self.clients[_id] = client
        return client



