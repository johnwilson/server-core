import zmq
import os
import redis
import logging
from uuid import uuid4
from zmq.eventloop import ioloop, zmqstream
from tornado.ioloop import IOLoop
from zmq.log.handlers import PUBHandler
import datetime
import time
import json
import zmq
import os
import sys
import argparse
import copy
from functools import partial

#===============================================================================
#   Content classes
#===============================================================================

class Node(object):

    reserved = ["__header__","_id"]
    dtformat = "%a %b %d %Y %H:%M:%S:%f"

    def __init__(self, document=None):
        if not document:
            self.name = ""
            self.type = "Node"
            self.id = None
            self.parent = None
            self.ispublic = False
            self.created = datetime.datetime.now().strftime(Node.dtformat)
            self.content = {}
        else:
            tmp = copy.deepcopy(document)
            header = tmp.pop("__header__")
            self.id = tmp.pop("_id")
            self.name = header["name"]
            self.type = header["type"]
            self.ispublic = header["public"]
            self.created = header["created"]
            if "parent" in header:
                self.parent = header["parent"]
            else:
                self.parent = None
            self.content = tmp
            
            # process additional header tags if any
            self.processHeader(header)
    
    def processHeader(self, header):
        pass
    
    def serialize(self):
        tmp = copy.deepcopy(self.content)
        tmp["__header__"] = {"name":self.name,
                             "public":self.ispublic,
                             "type":self.type,
                             "created":self.created}
        if self.id: tmp["_id"] = self.id
        if self.parent:
            tmp["__header__"]["parent"] = self.parent
        return tmp
    
    def __copy__(self):
        tmp = self.serialize()
        tmp["_id"] = None
        tmp["__header__"]["parent"] = None
        newnode = type(self)(tmp)
        return newnode

class File(Node):
    def __init__(self, document=None):
        Node.__init__(self, document)
        if not document:
            self.type = "File"
            self.filepointer = ""
            self.size = 0
            self.mime = ""
            
    def processHeader(self, header):
        self.filepointer = header["filepointer"]
        self.size = header["size"]
        self.mime = header["mime"]
    
    def serialize(self):
        tmp = Node.serialize(self)
        tmp["__header__"]["filepointer"] = self.filepointer
        tmp["__header__"]["size"] = self.size
        tmp["__header__"]["mime"] = self.mime
        return tmp

class Directory(Node):
    def __init__(self, document=None):
        Node.__init__(self, document)
        if not document:
            self.type = "Directory"

#===============================================================================
#   Content helpers
#===============================================================================

def GetMimeList():
    return {".css":"text/css",
            ".csv":"text/csv",
            ".html":"text/html",
            ".js":"text/javascript",
            ".txt":"text/plain",
            ".xml":"text/xml",
            ".json":"application/json",
            ".gif":"image/gif",
            ".jpg":"image/jpeg",
            ".jpeg":"image/jpeg",
            ".png":"image/png",
            ".svg":"image/svg+xml"}

#===============================================================================
#   Response message formatting
#===============================================================================

# General
def SuccessResponse(data, **kargs):
    _data = {"status":"ok","data":data}
    for key in kargs:
        if key not in ["status","data"]:
            _data[key] = kargs[key]
    return _data

def ErrorResponse(message, code="BE100", errortype="error"):
    _data = {"status":"error",
             "type":errortype,
             "msg":message,
             "code":code}
    return _data

# Internal Error messages
INT_ServiceError = partial(ErrorResponse, code="BE101", errortype="service_error")
INT_CommandError = partial(ErrorResponse, code="BE102", errortype="command_error")
INT_TimeoutError = partial(ErrorResponse, code="BE103", errortype="req_timeout_error")
INT_DataStoreError = partial(ErrorResponse, code="BE104", errortype="datastore_error")
INT_SessionError = partial(ErrorResponse, code="BE105", errortype="session_error")

# Client facing Error messages
ZeroResultError = partial(ErrorResponse, code="BE201", errortype="zero_result_error")
RequestDeniedError = partial(ErrorResponse, code="BE202", errortype="req_denied_error")
InvalidRequestError = partial(ErrorResponse, code="BE203", errortype="req_invalid_error")
AccountLimitError = partial(ErrorResponse, code="BE204", errortype="account_limit_error")


#===============================================================================
#   Logging
#===============================================================================

class BytengineLogger(PUBHandler):
    def __init__(self, interface_or_socket, context=None):
        PUBHandler.__init__(self, interface_or_socket, context)
        self.formatters = {
            logging.DEBUG: logging.Formatter("%(asctime)-6s: %(name)s - %(levelname)s %(filename)s:%(lineno)d - %(message)s\n"),
            logging.INFO: logging.Formatter("%(asctime)-6s: %(name)s - %(message)s\n"),
            logging.WARN: logging.Formatter("%(asctime)-6s: %(name)s - %(levelname)s %(filename)s:%(lineno)d - %(message)s\n"),
            logging.ERROR: logging.Formatter("%(asctime)-6s: %(name)s - %(levelname)s %(filename)s:%(lineno)d - %(message)s - %(exc_info)s\n"),
            logging.CRITICAL: logging.Formatter("%(asctime)-6s: %(name)s - %(levelname)s %(filename)s:%(lineno)d - %(message)s\n")}

#-------------------------------------------------------------------------------
#    Service and Command Servers
#-------------------------------------------------------------------------------

class BytengineError(Exception):
    def __init__(self, value):
        self.message = value["msg"]
        self.code = value["code"]
        self.error_type = value["type"]
    def __str__(self):
        txt = "Error[{0}]: {1}".format(self.code,self.message)
        return txt

#class Unauthorized(BytengineError): pass

class Service(object):

    def __init__(self, id, name="test", configfile=None):
        self.name = name
        self.id = id
        
        if not configfile:
            configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        self.configreader = json.load(open(configfile,"r"))
        
        self.ioloop = IOLoop(ioloop.ZMQPoller())
        self.ctx = zmq.Context()

        # request stream/socket
        socket = self.ctx.socket(zmq.PULL)
        socket.connect(self.configreader["services"][self.name]["address"])
        self.request_stream = zmqstream.ZMQStream(socket, io_loop=self.ioloop)
        self.request_stream.on_recv_stream(self.handleRequest)
        
        # response socket
        self.response_sock = self.ctx.socket(zmq.PUB)
        self.response_sock.connect(self.configreader["bytengine"]["services"]["rep_address"])
        
        # logging
        pub = self.ctx.socket(zmq.PUB)
        pub.setsockopt(zmq.HWM,1000)
        pub.connect(self.configreader["bytengine"]["services"]["logging_address"])
        self.logger = logging.getLogger("%s_%s" % (self.name, self.id))
        self.logger.setLevel(logging.INFO)
        handler = BytengineLogger(pub)
        self.logger.addHandler(handler)
        
    def handleRequest(self,stream, message):
        _parts = message[0].split(":",1)
        assert len(_parts) == 2, "request pointer message format invalid"
        
        # get request from redis
        r_server = self.redisConnect()
        _pointer = _parts[1].strip()
        _req = r_server.lrange(_pointer,0,-1)        
        _parts = _req[1].split(":",2)        
        _clientid = _req[0]
        _cmdtype = _parts[0].strip()
        _cmdname = _parts[1].strip()
        _cmdparams = _parts[2].strip()
        try:
            processed = self.processRequest(_cmdname, _cmdparams)
        except Exception, e: # uncaught error
            self.logger.exception(e)
            processed = ErrorResponse("service error. check log files")
        
        # convert result dict to json
        processed_json = json.dumps(processed)
        
        # save reply back to redis
        response_parts = [_clientid,processed_json]
        r_server.delete(_pointer)
        r_server.rpush(_pointer, *response_parts)
        response = u"POINTER:%s" % _pointer
        self.response_sock.send_string(response)
        
    def processRequest(self, cmd_name, cmd_params): pass
    
    def redisConnect(self):
        return redis.Redis(host=self.configreader["redis"]["host"],
                           port=self.configreader["redis"]["port"],
                           db=self.configreader["redis"]["memorydb"])
        
    def run(self):
        msg = "starting service %s[%s] ..." % (self.name, self.id)
        self.logger.info(msg)
        self.ioloop.start()
        
    def shutdown(self):
        self.ioloop.stop()
        
class OptionParsingError(RuntimeError):
    def __init__(self, msg):
        self.msg = msg

class OptionParsingExit(Exception):
    def __init__(self, status, msg):
        self.msg = msg
        self.status = status
        
class ModifiedOptionParser(argparse.ArgumentParser):
    def error(self, msg):
        raise OptionParsingError(msg)

    def exit(self, status=0, msg=None):
        raise OptionParsingExit(status, msg)

class CommandServer(object):
    def __init__(self, id, name="", configfile=None, repositoryfile=None):
        self.name = name
        self.id = id
        
        if not configfile:
            configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        self.configreader = json.load(open(configfile,"r"))
        
        if not repositoryfile:
            repositoryfile = os.path.join(os.path.dirname(__file__),"..","conf","commandrepository.json")
        self.repository = json.load(open(repositoryfile,"r"))
        
        self.ioloop = IOLoop(ioloop.ZMQPoller())
        self.ctx = zmq.Context()

        # request stream/socket
        socket = self.ctx.socket(zmq.PULL)
        socket.connect(self.configreader["commands"][self.name]["address"])
        self.request_stream = zmqstream.ZMQStream(socket, io_loop=self.ioloop)
        self.request_stream.on_recv_stream(self.handleRequest)
        
        # response socket
        self.response_sock = self.ctx.socket(zmq.PUB)
        self.response_sock.connect(self.configreader["bytengine"]["commands"]["rep_address"])
        
        # logging
        pub = self.ctx.socket(zmq.PUB)
        pub.setsockopt(zmq.HWM,1000)
        pub.connect(self.configreader["bytengine"]["commands"]["logging_address"])
        self.logger = logging.getLogger("%s_%s" % (self.name, self.id))
        self.logger.setLevel(logging.INFO)
        handler = BytengineLogger(pub)
        self.logger.addHandler(handler)
    
    def handleRequest(self,stream, message):
        _parts = message[0].split(":",1)
        assert len(_parts) == 2, "request pointer message format invalid"
        # get request from redis
        r_server = self.redisConnect()
        _namespace = _parts[0].strip()
        _pointer = _parts[1].strip()
        _req = r_server.lrange(_pointer,0,-1)        
        _clientid = _req[0]
        _cmd = _req[1]
        _session = _req[2].strip()
        _attachment = _req[3].strip()
        try:
            _cmd = _cmd.lstrip()
            _cmd_parts = _cmd.split(None,1)
            assert len(_cmd_parts) > 0, "Invalid command format"
            _cmd_list = self.repository[self.name]["commands"]
            if _cmd_parts[0] in _cmd_list:
                _function_name = _cmd_list[_cmd_parts[0]]["function"]
            else:
                raise BytengineError(INT_CommandError("command '%s' not found" % _cmd_parts[0]))
            _function = getattr(self, _function_name)
            processed = _function(_cmd, _session, _attachment)
        except OptionParsingError, e:
            self.logger.exception(e.msg)
            processed = INT_CommandError(e.msg)
        except BytengineError, e:
            self.logger.exception(e.message)
            processed = INT_CommandError(e.message, code=e.code, errortype=e.error_type)
        except OptionParsingExit, e:
            self.logger.exception(e.msg)
            processed = INT_CommandError(e.msg)
        except AssertionError, e:
            self.logger.exception(e)
            processed = INT_CommandError(str(e))
        except AttributeError, e:
            self.logger.exception(e)
            processed = INT_CommandError("command '%s' discovery failed" % _cmd_parts[0])
        except Exception, e:
            self.logger.exception(e)
            processed = INT_CommandError("uncaught bytengine error. contact admin")
        
        # save reply back to redis
        processed_json = json.dumps(processed)
        response_parts = [_clientid,processed_json]
        r_server.delete(_pointer)
        r_server.rpush(_pointer, *response_parts)
        response = u"POINTER:%s" % _pointer
        self.response_sock.send_string(response)
        
    def redisConnect(self):
        return redis.Redis(host=self.configreader["redis"]["host"],
                           port=self.configreader["redis"]["port"],
                           db=self.configreader["redis"]["memorydb"])
        
    def run(self):
        msg = "starting command server %s[%s] ..." % (self.name, self.id)
        self.logger.info(msg)
        self.ioloop.start()
        
    def shutdown(self):
        self.ioloop.stop()
