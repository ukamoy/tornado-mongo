from dayu.portainer import *
from datetime import datetime
import tarfile
from io import BytesIO


class APIAuthKeeper(object):

    def __init__(self, api, username, password, autoRefresh=7*3600):
        assert isinstance(api, PortainerAPI)
        self.api = api
        self.autoRefresh = autoRefresh
        self.username = username
        self.password = password
        self.lastAuthTime = 0
    
    def auth(self):
        self.api.auth(self.username, self.password)
        self.lastAuthTime = datetime.now().timestamp()
    
    def ensureAuth(self):
        if not self.api.isAuthed() or (datetime.now().timestamp() - self.lastAuthTime > self.autoRefresh):
            self.auth()


class PortainerDeployer(object):

    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.headers = {}
        self.api = PortainerAPI(host, self.headers)
        self.keeper = APIAuthKeeper(self.api, username, password)
        self.serverInfo = {}
        self.serverMap = {}
        self._servers = {}
    
    def grabServerInfo(self):
        self.keeper.ensureAuth()
        endpoints = self.api.endpoints
        eps = endpoints.getAll()
        self.serverInfo = eps
        self.serverMap = {ep["Name"]: ep["Id"] for ep in eps}
    
    def getServerById(self, _id):
        client = self.api.endpoints.dockerClient(_id)
        server = ServerDeployer(client, self.keeper)
        return server

    def getServerByName(self, name):
        if name in self.serverMap:
            return self.getServerById(self.serverMap[name])
        else:
            self.grabServerInfo()
            if name not in self.serverMap:
                raise KeyError("Server: %s not exists." % name)
            else:
                return self.getServerById(self.serverMap[name])


class ServerDeployer(object):

    def __init__(self, client, keeper):
        assert isinstance(client, docker.DockerClient)
        assert isinstance(keeper, APIAuthKeeper)
        self.client = client
        self.keeper = keeper
    
    def create(self, image, name, source):
        self.keeper.ensureAuth()
        container = self.client.containers.create(
            image,
            command="vnpy run terminal",
            name=name,
            network_mode="host",
            working_dir="/strategy",
            volumes={
                f"{name}": {
                    "bind": "/strategy",
                    "mode": "rw"
                },
                "/etc/localtime": {
                    "bind": "/etc/localtime",
                    "mode": "ro"
                },
                "vnpy": {
                    "bind": "/root/.vnpy",
                    "mode": "rw"
                }
            },
        )
        if isinstance(source, bytes):
            archive = source
        else:
            archive = makeArchive("strategy", source)
        return container.put_archive(
            "/strategy",
            archive
        )
    
    def start(self, name):
        self.keeper.ensureAuth()
        container = self.client.containers.get(name)
        container.start()
        container.reload()
        return container.status
    
    def stop(self, name):
        self.keeper.ensureAuth()
        container = self.client.containers.get(name)
        if container.status == "running":
            container.stop()
            r = container.wait()
            print(r)
            container.reload()
        return container.status

    def archive(self, name):
        self.keeper.ensureAuth()
        container = self.client.containers.get(name)
        bits, stat = container.get_archive("/strategy")
        print(stat)
        bio = BytesIO()
        for chunk in bits:
            bio.write(chunk)
        bio.seek(0)
        return bio.read()
    
    def remove(self, name):
        self.keeper.ensureAuth()
        container = self.client.containers.get(name)
        if container.status == "running":
            raise Exception("Container: %s running, unable to remove" % name)
        container.remove()
        volume = self.client.volumes.get(name)
        volume.remove()

    def get(self, name):
        try:
            container = self.client.containers.get(name)
        except:
            return None
        else:
            return container


def makeArchive(name, working_dir):
    bio = BytesIO()
    archive = tarfile.open(name, "w", bio)
    for name in os.listdir(working_dir):
        filename = os.path.join(working_dir, name)
        if os.path.isfile(filename):
            archive.add(filename, name)

    archive.close()
    bio.seek(0)
    return bio.read()
