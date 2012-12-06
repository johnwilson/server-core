import json
import zmq
import os
import logging
from zmq.eventloop import ioloop, zmqstream
from tornado.ioloop import IOLoop
import sdk, common

class Server(object):

    def __init__(self, id, configfile=None):
        self.id = id
        self.ioloop = IOLoop(ioloop.ZMQPoller())
        self.ctx = zmq.Context()
        
        if not configfile:
            configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        self.configreader = json.load(open(configfile,"r"))
        
        #-----------------------------------------------------------------------
        #   Web Request Worker
        #-----------------------------------------------------------------------
        
        self.rep_socket = self.ctx.socket(zmq.REP)
        self.rep_socket.connect(self.configreader["bytengine"]["web"]["rep_address"])
        self.rep_stream = zmqstream.ZMQStream(self.rep_socket, io_loop=self.ioloop)
        self.rep_stream.on_recv_stream(self.handleRequest)
        
        # logging
        pub = self.ctx.socket(zmq.PUB)
        pub.setsockopt(zmq.HWM,1000)
        pub.connect(self.configreader["bytengine"]["services"]["logging_address"])
        self.logger = logging.getLogger("webworker_%s" % self.id)
        self.logger.setLevel(logging.INFO)
        handler = common.BytengineLogger(pub)
        self.logger.addHandler(handler)
        
    def handleRequest(self,stream, message):
        try:
            sessionid = message[0]
            attachment = message[1]
            command = message[2]
            
            self.logger.info("webworker[{0}] Request: {1}".format(self.id,command))
            
            r = sdk.command_rpc(command, session=sessionid,
                                attachment=attachment, return_raw=True)
            stream.send_unicode(r)
        except Exception, e:
            self.logger.exception(e)
            txt = common.ErrorResponse(str(e), code='BE200', errortype='webworker_error')
            stream.send_unicode(json.dumps(txt))
    
    def shutdown(self):
        self.logger.info("stoping web request worker [%s]" % self.id)
        self.ioloop.stop()

    def run(self):
        self.logger.info("starting web request worker [%s]" % self.id)
        self.ioloop.start()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--id",action="store",type=int,default=1)
    parsed = parser.parse_args()
    
    svr = Server(id=parsed.id)
    
    try:
        svr.run()
    except KeyboardInterrupt:
        svr.shutdown()