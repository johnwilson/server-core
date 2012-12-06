import os
import sys
import json

import zmq
from zmq.eventloop import ioloop

ioloop.install()

import tornado
from tornado import web
from tornado.options import define, options

# add bytengine to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

from bytengine.application.core import webapi
from bytengine.application.core.routes import Route
from bytengine.application.web import *

#    Configure startup options
define("port", default=8000, help="run on the given port", type=int)
define("host", default="127.0.0.1", help="run on the given address", type=str)

def init(host, port):
    #   url configuration
    # read configuration file settings
    settings_f = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
    parser = json.load(open(settings_f))

    frontendpoint = parser["bytengine"]["web"]["req_address"]
    
    #   url configuration
    urls = [
        #   bytengine api and commands
        (r"/bfs", webapi.commandHandler, dict(bytengine_endpoint=frontendpoint)),
        (r"/bfs/formatted", webapi.prettyprintCommandHandler, dict(bytengine_endpoint=frontendpoint)),
        (r"/bfs/upload", webapi.attachmentUploadHandler, dict(bytengine_endpoint=frontendpoint)),
        (r"/bfs/download", webapi.attachmentDownloadHandler, dict(bytengine_endpoint=frontendpoint)),
        (r"/direct/(fd|fa)/(\w+)/([\w_./]+)", webapi.publicDataAccessHandler, dict(bytengine_endpoint=frontendpoint)),
        
        #   bytengine welcome
        (r"/", webapi.versionHandler)
        
    ] + Route.routes() + [(r".*", main.siteErrorHandler)]
    
    dir_templates = os.path.join(os.path.dirname(__file__),"..","web","templates")
    dir_static = os.path.join(os.path.dirname(__file__),"..","web","static")
    
    application = web.Application(handlers=urls,
                                  template_path=dir_templates,
                                  static_path=dir_static,
                                  debug=True)    
    application.listen(port, address=host)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print ' Interrupted'

if __name__ == "__main__":
    tornado.options.parse_command_line()
    init(options.host, options.port)