import json
import zmq
import os
import redis
import threading
from uuid import uuid4
from datetime import datetime
import hashlib
from zmq.eventloop import ioloop, zmqstream
from tornado.ioloop import IOLoop
import logging

#   Configure logging
formatter = logging.Formatter('%(message)s')
consoleLogger = logging.StreamHandler()
consoleLogger.setFormatter(formatter)
Logger = logging.getLogger("bytengine.server")
Logger.setLevel(logging.INFO)
Logger.addHandler(consoleLogger)

class Server(object):

    def __init__(self, configfile=None):
        self.ioloop = IOLoop(ioloop.ZMQPoller())
        self.ctx = zmq.Context()
        
        if not configfile:
            configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        self.configreader = json.load(open(configfile,"r"))
        
        #-----------------------------------------------------------------------
        #   Service Request Management Sockets
        #-----------------------------------------------------------------------

        # request socket: clients make requests at this address
        srv_req_socket = self.ctx.socket(zmq.ROUTER)
        srv_req_socket.bind(self.configreader["bytengine"]["services"]["req_address"])
        self.srv_req_stream = zmqstream.ZMQStream(srv_req_socket, io_loop=self.ioloop)
        self.srv_req_stream.on_recv_stream(self.pushServiceReq)
        
        self.services = {}
        _services = self.configreader["services"]
        for service in _services:
            if "address" in _services[service]:
                socket = self.ctx.socket(zmq.PUSH)
                socket.bind(_services[service]["address"])
                self.services[service] = socket
        
        # sub socket: bytengine listens on this address for service replies
        srv_sub_socket = self.ctx.socket(zmq.SUB)
        srv_sub_socket.setsockopt(zmq.SUBSCRIBE, "DATA")
        srv_sub_socket.setsockopt(zmq.SUBSCRIBE, "POINTER")
        srv_sub_socket.bind(self.configreader["bytengine"]["services"]["rep_address"])
        self.srv_sub_stream = zmqstream.ZMQStream(srv_sub_socket, io_loop=self.ioloop)
        self.srv_sub_stream.on_recv_stream(self.handleServiceReply)
        
        #-----------------------------------------------------------------------
        #   Command Request Management Sockets
        #-----------------------------------------------------------------------

        # request socket: clients make requests at this address
        cmd_req_socket = self.ctx.socket(zmq.ROUTER)
        cmd_req_socket.bind(self.configreader["bytengine"]["commands"]["req_address"])
        self.cmd_req_stream = zmqstream.ZMQStream(cmd_req_socket, io_loop=self.ioloop)
        self.cmd_req_stream.on_recv_stream(self.pushCommandReq)
        
        self.commands = {}
        _commands = self.configreader["commands"]
        for command in _commands:
            if "address" in _commands[command]:
                socket = self.ctx.socket(zmq.PUSH)
                socket.bind(_commands[command]["address"])
                self.commands[command] = socket
        
        # sub socket: bytengine listens on this address for command servers replies
        cmd_sub_socket = self.ctx.socket(zmq.SUB)
        cmd_sub_socket.setsockopt(zmq.SUBSCRIBE, "DATA")
        cmd_sub_socket.setsockopt(zmq.SUBSCRIBE, "POINTER")
        cmd_sub_socket.bind(self.configreader["bytengine"]["commands"]["rep_address"])
        self.cmd_sub_stream = zmqstream.ZMQStream(cmd_sub_socket, io_loop=self.ioloop)
        self.cmd_sub_stream.on_recv_stream(self.handleCommandReply)
        
        #-----------------------------------------------------------------------
        #   Web Request Router
        #-----------------------------------------------------------------------
        
        self.req_router_socket = self.ctx.socket(zmq.ROUTER)
        self.req_router_socket.bind(self.configreader["bytengine"]["web"]["req_address"])
        self.req_router_stream = zmqstream.ZMQStream(self.req_router_socket, io_loop=self.ioloop)
        self.req_router_stream.on_recv_stream(self.sendToWebReqDealer)
        
        #-----------------------------------------------------------------------
        #   Web Request Dealer
        #-----------------------------------------------------------------------
        
        self.req_dealer_socket = self.ctx.socket(zmq.DEALER)
        self.req_dealer_socket.bind(self.configreader["bytengine"]["web"]["rep_address"])
        self.req_dealer_stream = zmqstream.ZMQStream(self.req_dealer_socket, io_loop=self.ioloop)
        self.req_dealer_stream.on_recv_stream(self.sendToWebReqRouter)
        
        #-----------------------------------------------------------------------
        #   Logging Sockets
        #-----------------------------------------------------------------------
        
        cmd_log_socket = self.ctx.socket(zmq.SUB)
        cmd_log_socket.setsockopt(zmq.SUBSCRIBE, "")
        cmd_log_socket.bind(self.configreader["bytengine"]["commands"]["logging_address"])
        self.cmd_log_stream = zmqstream.ZMQStream(cmd_log_socket, io_loop=self.ioloop)
        self.cmd_log_stream.on_recv_stream(self.sendToLogger)
        
        srv_log_socket = self.ctx.socket(zmq.SUB)
        srv_log_socket.setsockopt(zmq.SUBSCRIBE, "")
        srv_log_socket.bind(self.configreader["bytengine"]["services"]["logging_address"])
        self.srv_log_stream = zmqstream.ZMQStream(srv_log_socket, io_loop=self.ioloop)
        self.srv_log_stream.on_recv_stream(self.sendToLogger)
        
        web_log_socket = self.ctx.socket(zmq.SUB)
        web_log_socket.setsockopt(zmq.SUBSCRIBE, "")
        web_log_socket.bind(self.configreader["bytengine"]["web"]["logging_address"])
        self.web_log_stream = zmqstream.ZMQStream(web_log_socket, io_loop=self.ioloop)
        self.web_log_stream.on_recv_stream(self.sendToLogger)
        
    def sendToWebReqDealer(self,stream, message):
        self.req_dealer_socket.send_multipart(message)
        
    def sendToWebReqRouter(self,stream, message):
        self.req_router_socket.send_multipart(message)
        
    def pushServiceReq(self,stream, message):
        clientid = message[0]
        data = message[2]
        
        try:
            _service, _req = self.parseServiceReq(data)
            if not _service in self.services:
                _err = "service '%s' not found" % _service
                reply = json.dumps({"status":"error","msg":_err,"type":"ServiceNotFound"})
                stream.send(clientid, zmq.SNDMORE)
                stream.send('', zmq.SNDMORE)
                stream.send_unicode(unicode(reply))
            else:                
                pointer = hashlib.sha224(uuid4().hex).hexdigest()            
                r_server = self.redisConnect()
                
                # add client id to data
                _data = [clientid,_req]
                saved = r_server.rpush(pointer, *_data)
                if not saved:
                    _err = "request data couldn't be processed"
                    reply = json.dumps({"status":"error","msg":_err,"type":"request_error"})
                    stream.send(clientid, zmq.SNDMORE)
                    stream.send('', zmq.SNDMORE)
                    stream.send_unicode(unicode(reply))
                    # delete pointer from redis
                    r_server.delete(pointer)
                    print "error saving command request pointer"
                else:
                    # set memory item timeout
                    r_server.expire(pointer,self.configreader["bytengine"]["req_mem_timeout"])
                    # push service
                    _msg = "%s:%s" % (_service,pointer)
                    _socket = self.services[_service]
                    _socket.send_string(_msg)
            
        except AssertionError, err:
            reply = json.dumps({"status":"error","msg":str(err),"type":"request_error"})
            stream.send(clientid, zmq.SNDMORE)
            stream.send('', zmq.SNDMORE)
            stream.send_unicode(unicode(reply))
    
    def parseServiceReq(self, message):
        """
        data format:
            service : command_type : command_name : arguments
        """
        _parts = message.split(":",1)
        assert len(_parts) == 2, "service request message format invalid."        
        _service = _parts[0].strip().lower()
        _rest = _parts[1]
        return _service, _rest
    
    def pushCommandReq(self,stream, message):
        clientid = message[0]
        data = message[2]
        
        try:
            _namespace, _data = self.parseCommandReq(data)
            if not _namespace in self.commands:
                _err = "command namespace '%s' not found" % _namespace
                reply = json.dumps({"status":"error","msg":_err,"type":"CommandNamespaceNotFound"})
                stream.send(clientid, zmq.SNDMORE)
                stream.send('', zmq.SNDMORE)
                stream.send_unicode(unicode(reply))
            else:
                pointer = hashlib.sha224(uuid4().hex).hexdigest()            
                r_server = self.redisConnect()
                
                # add client id to data
                _data.insert(0, clientid)            
                saved = r_server.rpush(pointer, *_data)
                if not saved:
                    _err = "request data couldn't be processed"
                    reply = json.dumps({"status":"error","msg":_err,"type":"request_error"})
                    stream.send(clientid, zmq.SNDMORE)
                    stream.send('', zmq.SNDMORE)
                    stream.send_unicode(unicode(reply))
                    # delete pointer from redis
                    r_server.delete(pointer)
                    print "error saving command request pointer"
                else:
                    # set memory item timeout
                    r_server.expire(pointer,self.configreader["bytengine"]["req_mem_timeout"])
                    # push namspace
                    _msg = "%s:%s" % (_namespace,pointer)
                    _socket = self.commands[_namespace]
                    _socket.send_string(_msg)
            
        except AssertionError, err:
            reply = json.dumps({"status":"error","msg":str(err),"type":"request_error"})
            stream.send(clientid, zmq.SNDMORE)
            stream.send('', zmq.SNDMORE)
            stream.send_unicode(unicode(reply))
    
    def handleReply(self, stream, message):
        try:
            _pointerid = self.parseReply(message[0])
            r_server = self.redisConnect()
            _reply = r_server.lrange(_pointerid,0,-1)
            stream.send(_reply[0], zmq.SNDMORE)
            stream.send('', zmq.SNDMORE)
            stream.send_unicode(unicode(_reply[1]))
            r_server.delete(_pointerid)
        except AssertionError, err:
            print err
            
    def handleCommandReply(self, stream, message):
        self.handleReply(self.cmd_req_stream, message)
        
    def handleServiceReply(self, stream, message):
        self.handleReply(self.srv_req_stream, message)
    
    def parseCommandReq(self, message):
        """
        data format:
            session_id : attachment : namespace : command command_data
        """
        
        _parts = message.split(":",3)
        assert len(_parts) == 4, "command request message format invalid."        
        _cmd = _parts[3]
        _attachment = _parts[1].strip()
        _namespace = _parts[2].strip()
        if len(_namespace) < 1:
            _namespace = "core"
        _session = _parts[0].strip()
        return _namespace, [_cmd,_session,_attachment]
    
    def parseReply(self, message):
        """
        data format:
            POINTER : PointerId
        """
        _parts = message.split(":",2)
        assert len(_parts) == 2, "command reply message format invalid."
        return _parts[1].strip()
    
    def sendToLogger(self, stream, message):
        Logger.info(message[1])
    
    def redisConnect(self):
        return redis.Redis(host=self.configreader["redis"]["host"],
                           port=self.configreader["redis"]["port"],
                           db=self.configreader["redis"]["memorydb"])
    
    def shutdown(self):
        print "stoping bytengine server ..."
        self.ioloop.stop()

    def run(self):
        print "starting bytengine server ..."        
        self.ioloop.start()

if __name__ == '__main__':
    svr = Server()
    
    try:
        svr.run()
    except KeyboardInterrupt:
        svr.shutdown()