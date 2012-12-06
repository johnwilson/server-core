import sys
import os
import time

# add bytengine to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

from bytengine.application.core import sdk

#_subject = "test from bytengine"
#_to = ["wilsonfiifi@gmail.com"]
#_from = "noreply@ineedquickly.com"
#_text = "Hello World from Python!"
#_host = "mail.infinitebluecloud.com"
#_pass = "8447bHmh3S"
#_author = "ineedquickly"
#
#data = {"subject":_subject,
#        "to":_to,
#        "from":_from,
#        "content":_text,
#        "host":_host,
#        "password":_pass,
#        "author":_author}
#
#ticket = sdk.cmd_sendmail(**data)
count = 10
while count > 0:
    count -=1
    print "mail status", sdk.cmd_emailstatus(ticket="sendmail:req:efbbeeede1fd436ab4414d82d7dc7c68")
    time.sleep(10)