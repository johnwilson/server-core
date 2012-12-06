import os
import json
import logging
from common import Service
import common
import smtplib
import email.utils
from email.mime.text import MIMEText
from uuid import uuid4
import redis
from zmq.eventloop.ioloop import PeriodicCallback

class EmailService(Service):
    
    def __init__(self, id, name="email", configfile=None):
        Service.__init__(self, id, name, configfile)
        self.pending_emails_key = "pending.mails"
        
    def processRequest(self, command, command_data):
        _request = json.loads(command_data)
        if command == "email.send":
            return self.cmd_sendmail(**_request)
        else:
            return common.requestMethodNotFound("command '%s' doesn't exist" % command)
        
    def cmd_sendmail(self, **kwargs):
        _subject = kwargs["subject"]
        _to = ",".join(kwargs["to"])
        _from = kwargs["from"]
        _content = kwargs["content"]
        _mailserver = kwargs["mailserver"]
        _password = kwargs["password"]
        _author = kwargs["author"]
        
        _req_id = uuid4().hex
        _key = "sendmail:req:{0}".format(_req_id)        
        _path = os.path.join(self.configreader["services"][self.name]["tmpdir"],_req_id)
        
        # build email
        msg = MIMEText(_content.encode("utf-8"), "plain",'UTF-8')
        msg.set_unixfrom('author')
        msg["To"] = email.utils.formataddr(('Recipient', _to))
        msg["From"] = email.utils.formataddr((_author, _from))
        msg["Subject"] = _subject
        _body = msg.as_string()
        
        _f = open(_path,"w+")
        _f.write(_body)
        _f.close()
        
        r_server = self.redisEmailConnect()
        r_server.hset(_key,"to",_to)
        r_server.hset(_key,"author",_author)
        r_server.hset(_key,"from",_from)
        r_server.hset(_key,"mailserver",_mailserver)
        r_server.hset(_key,"password",_password)
        r_server.hset(_key,"contentpath",_path)
        r_server.hset(_key,"status","pending")
        r_server.rpush(self.pending_emails_key,_key)
        
        return common.SuccessResponse(_key)
    
    def cmd_processmails(self, **kwargs):
        self.logger.info("checking mail requests")
        r_server = self.redisEmailConnect()
        while r_server.llen(self.pending_emails_key) > 0:
            _key = r_server.lpop(self.pending_emails_key)
            data = r_server.hgetall(_key)
            if len(data) > 0:
                self.logger.info("processing mail")
                try:
                    _f = open(data["contentpath"],"r")
                    _body = _f.read()
                    _f.close()
                    server = smtplib.SMTP(data["mailserver"])
                    server.ehlo()
                    server.starttls()
                    server.ehlo
                    server.login(data["from"], data["password"])
                    server.sendmail(data["from"], data["to"].split(","), _body)
                    server.quit()
                    
                    r_server.hset(_key,"status","sent")
                    os.unlink(data["contentpath"])
                except Exception, e:
                    self.logger.exception(e)
                    r_server.hset(_key,"status","Error: {0}".format(str(e)))
                _timeout = self.configreader["services"][self.name]["timeout"]
                r_server.expire(_key,_timeout)
            
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
    
    def run(self):
        _period = 1000 * self.configreader["services"][self.name]["checkmail_interval"]
        beat = PeriodicCallback(self.cmd_processmails,
                                _period,
                                io_loop=self.ioloop)
        beat.start()
        Service.run(self)
        
if __name__ == '__main__':    
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--id",action="store",type=int,default=1)
    parsed = parser.parse_args()
    
    s = EmailService(id=parsed.id)
    try:
        s.run()
    except KeyboardInterrupt:
        print "\nexiting"