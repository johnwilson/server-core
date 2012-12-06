import os
import json
import logging
from common import Service
import common
import redis
from zmq.eventloop.ioloop import PeriodicCallback

class EmailCheckService(Service):
    
    def __init__(self, id, name="emailcheck", configfile=None):
        Service.__init__(self, id, name, configfile)
        
    def processRequest(self, command, command_data):
        _request = json.loads(command_data)
        if command == "email.checkstatus":
            return self.cmd_checkmailstatus(**_request)
        else:
            return common.requestMethodNotFound("command '%s' doesn't exist" % command)
        
    def cmd_checkmailstatus(self, **kwargs):
        ticket = kwargs["ticket"]
        r_server = self.redisEmailConnect()
        data = r_server.hget(ticket,"status")
        if not data:
            return common.INT_ServiceError("emailrequest not found")
        return common.SuccessResponse(data)
        
    def redisEmailConnect(self):
        return redis.Redis(host=self.configreader["redis"]["host"],
                           port=self.configreader["redis"]["port"],
                           db=self.configreader["redis"]["emaildb"])
    
if __name__ == '__main__':    
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--id",action="store",type=int,default=1)
    parsed = parser.parse_args()
    
    s = EmailCheckService(id=parsed.id)
    try:
        s.run()
    except KeyboardInterrupt:
        print "\nexiting"