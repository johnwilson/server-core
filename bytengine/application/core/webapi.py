import logging
import json
import zmq
from zmq.eventloop import zmqstream
from tornado import web
import os

import sys
# add bytengine to python path
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

#   Configure logging
formatter = logging.Formatter('%(asctime)-6s: %(name)s - %(levelname)s - %(message)s')
consoleLogger = logging.StreamHandler()
consoleLogger.setFormatter(formatter)
api_logger = logging.getLogger("bytengine.webapi")
api_logger.setLevel(logging.INFO)
api_logger.addHandler(consoleLogger)

class commandHandler(web.RequestHandler):
    def initialize(self, bytengine_endpoint):
        self._bytengine_endpoint = bytengine_endpoint

    @web.asynchronous
    def post(self):
        command = self.get_argument("command", default="")
        sessionid = self.get_argument("ticket", default="")
        attachment = ""
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.connect(self._bytengine_endpoint)
        s.send_unicode(sessionid, zmq.SNDMORE)
        s.send_unicode(attachment, zmq.SNDMORE)
        s.send_unicode(command)
        self.stream = zmqstream.ZMQStream(s)
        self.stream.on_recv(self.handle_reply)

    def handle_reply(self, msg):
        # finish web request with worker's reply
        reply = msg[0]        
        self.stream.close()
        self.write(reply)
        self.set_header("Content-Type","application/json")
        self.finish()

# inherit commandHandler and override 'handle_reply' method        
class prettyprintCommandHandler(commandHandler):
    def handle_reply(self, msg):
        # finish web request with worker's reply
        reply = msg[0]        
        self.stream.close()
        # convert to json
        tmp = json.loads(reply)
        reply = json.dumps(tmp, indent=2)
        self.write(reply)
        self.set_header("Content-Type","text/plain")
        self.finish()

class publicDataAccessHandler(web.RequestHandler):
    def initialize(self, bytengine_endpoint):
        self._bytengine_endpoint = bytengine_endpoint

    @web.asynchronous
    def get(self, datatype, database, filepath):
        if datatype == "fa":
            command = "directaccess %s %s -a" % (database, filepath)
        elif datatype == "fd":
            command = "directaccess %s %s -j" % (database, filepath)
        else:
            self.set_status(404)
            self.finish()
        
        sessionid = ""
        attachment = ""        
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.connect(self._bytengine_endpoint)
        s.send_unicode(sessionid, zmq.SNDMORE)
        s.send_unicode(attachment, zmq.SNDMORE)
        s.send_unicode(command)
        self.stream = zmqstream.ZMQStream(s)
        if datatype == "fa":
            self.stream.on_recv(self.handle_attachmentreply)
        elif datatype == "fd":
            self.stream.on_recv(self.handle_jsonreply)        

    def handle_jsonreply(self, msg):
        # finish web request with worker's reply
        reply = msg[0]
        self.stream.close()
        _jsondata = json.loads(reply)
        if _jsondata["status"] != "ok":
            self.set_status(404)
            self.finish()
        else:
            self.write(_jsondata["data"])
            self.finish()
    
    def handle_attachmentreply(self, msg):
        # finish web request with worker's reply
        reply = msg[0]
        self.stream.close()
        _jsondata = json.loads(reply)
        if _jsondata["status"] != "ok":
            self.set_status(404)
            self.finish()
        elif _jsondata["data"] == "":
            self.set_status(404)
            self.finish()
        else:
            _attach_name = os.path.basename(_jsondata["data"]["attachment"])
            _database = _jsondata["data"]["database"]
            _file_name = _jsondata["data"]["filename"]
            _redirect = "/attachments/%s/%s" % (_database,_attach_name)
            _extension = _jsondata["data"]["extension"]            
            self.set_header("Content-Type",_jsondata["data"]["mime"])
            self.set_header("Content-Disposition","inline; filename=%s" % _file_name)
            self.set_header("X-Accel-Redirect",_redirect)
            self.finish()

class attachmentUploadHandler(web.RequestHandler):    
    def initialize(self, bytengine_endpoint):
        self._bytengine_endpoint = bytengine_endpoint

    @web.asynchronous
    def post(self):
        attachment = self.get_argument("file.path",None)        
        command = self.get_argument("command", default="")
        sessionid = self.get_argument("ticket", default="")
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.connect(self._bytengine_endpoint)
        s.send_unicode(sessionid, zmq.SNDMORE)
        s.send_unicode(attachment, zmq.SNDMORE)
        s.send_unicode(command)
        self.stream = zmqstream.ZMQStream(s)
        self.stream.on_recv(self.handle_reply)

    def handle_reply(self, msg):
        # finish web request with worker's reply
        reply = msg[0]
        self.stream.close()
        self.write(reply)
        self.set_header("Content-Type","application/json")
        self.finish()
        
class attachmentDownloadHandler(web.RequestHandler):    
    def initialize(self, bytengine_endpoint):
        self._bytengine_endpoint = bytengine_endpoint

    @web.asynchronous
    def post(self):        
        attachment = ""
        command = self.get_argument("command", default="")
        sessionid = self.get_argument("ticket", default="")
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.connect(self._bytengine_endpoint)
        s.send_unicode(sessionid, zmq.SNDMORE)
        s.send_unicode(attachment, zmq.SNDMORE)
        s.send_unicode(command)
        self.stream = zmqstream.ZMQStream(s)
        self.stream.on_recv(self.handle_reply)        

    def handle_reply(self, msg):
        # finish web request with worker's reply
        reply = msg[0]
        self.stream.close()
        response = json.loads(reply)
        if "status" in response and response["status"] == "ok":
            _redirect = "/attachments/%s/%s" % (response["data"]["database"],
                                                response["data"]["file"])
            self.set_header("Content-Type",response["data"]["mime"])
            self.set_header("Content-Disposition","inline; filename=bytengine_attachment")
            self.set_header("X-Accel-Redirect",_redirect)
        else:
            self.write(response)
            self.set_header("Content-Type","application/json")
        self.finish()

class versionHandler(web.RequestHandler):
    def get(self):
        self.write({"bytengine":"welcome","version":"0.3.1"})