import requests
from requests.exceptions import ConnectionError
import json
import os

class Connection(object):
    def __init__(self, username, password, database=None, host="127.0.0.1", port=8500):
        self._host = host
        self._port = port
        self._ticket = None
        self.timeout = 10 # duration in seconds

        if database:
            command = "login -u='{username}' -p='{password}' -d='{database}'".format(username=username,
                                                                                     password=password,
                                                                                     database=database)
        else:
            command = "login -u='{username}' -p='{password}'".format(username=username,
                                                                     password=password)
        try:
            values = {"command":command, "namespace":""}
            url = "http://%s:%s/bfs" % (self._host, self._port)
            r = requests.post(url, data=values, timeout=self.timeout)
            if not r.status_code == 200:
                raise Exception("bytengine server error. '%s'" % r.status_code)
            reply = json.loads(r.content)
            if reply["status"] == "ok":
                self._ticket = reply["data"]["ticket"]
            else:
                raise Exception(reply["msg"])
        except ConnectionError:
            raise Exception("Connection to bytengine server could not be made.")

    def command(self, text, namespace=""):
        try:
            url = "http://%s:%s/bfs" % (self._host, self._port)
            values = {"command":text, "ticket":self._ticket, "namespace":namespace}
            r = requests.post(url, data=values, timeout=self.timeout)
            if not r.status_code == 200:
                raise Exception("bytengine server error. '%s'" % r.status_code)
            cmd = json.loads(r.content)
            if cmd["status"] == "ok":
                return cmd["data"]
            else:
                raise Exception(cmd["msg"])
        except ConnectionError:
            raise Exception("Connection to bytengine server could not be made.")

    def uploadfile(self, remote_filepath, local_filepath):
        try:
            # check if file to upload exists
            if not os.path.exists(local_filepath):
                raise Exception("File to upload not found")
                return
            if not os.path.isfile(local_filepath):
                raise Exception("'%s' isn't a file" % upload)
                return

            # connect to bytengine
            data = {"command":"upload %s" % remote_filepath, "ticket":self._ticket, "namespace":""}
            url = "http://%s:%s/bfs/upload" % (self._host, self._port)

            r = requests.post(url, data=data, files={"file":open(local_filepath,'rb')}, timeout=self.timeout)
            if not r.status_code == 200:
                raise Exception("bytengine server error. '%s'" % r.status_code)
            cmd = json.loads(r.content)
            if cmd["status"] == "ok":
                return cmd["data"]
            else:
                raise Exception(cmd["msg"])
        except ConnectionError:
            raise Exception("Connection to bytengine server could not be made.")

    def downloadfile(self, remote_filepath, local_filepath):
        try:
            # connect to bytengine
            data = {"command":"download %s" % remote_filepath, "ticket":self._ticket, "namespace":""}
            url = "http://%s:%s/bfs/download" % (self._host, self._port)

            r = requests.post(url, data=data, timeout=self.timeout)
            if not r.status_code == 200:
                raise Exception("bytengine server error. '%s'" % r.status_code)

            if "application/json" in r.headers["content-type"]:
                cmd = json.loads(r.content)
                if cmd["status"] == "ok":
                    return cmd["data"]
                else:
                    raise Exception(cmd["msg"])
            elif "application/octet-stream" in r.headers["content-type"]:
                binary_file = open(local_filepath,"wb")
                binary_file.write(r.content)
                binary_file.close()
                return "ok"
        except ConnectionError:
            raise Exception("Connection to bytengine server could not be made.")

    @property
    def host(self): return self._host

    @property
    def port(self): return self._port

    @property
    def id(self): return self._ticket