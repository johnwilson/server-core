import sys
import os

# add bytengine to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

import threading
from bytengine.application.core import bfs, parser, command, broker, webworker, mailer, mailcheck

_bfs = bfs.BFSService(1)
_parser = parser.ParserService(1)
_cmdsvr = command.Server(1)
_btsvr = broker.Server()
_wrwkr = webworker.Server(1)
_email = mailer.EmailService(1)
_emailchceck = mailcheck.EmailCheckService(1)
    
def main():
    t_btsvr = threading.Thread(target=_btsvr.run)
    t_btsvr.start()
    
    t_bfs = threading.Thread(target=_bfs.run)
    t_bfs.start()
    
    t_parser = threading.Thread(target=_parser.run)
    t_parser.start()
    
    t_cmdsvr = threading.Thread(target=_cmdsvr.run)
    t_cmdsvr.start()
    
    t_wrwkr = threading.Thread(target=_wrwkr.run)
    t_wrwkr.start()
    
    t_email = threading.Thread(target=_email.run)
    t_email.start()
    
    t_emailchceck = threading.Thread(target=_emailchceck.run)
    t_emailchceck.start()
    
    while True:
        pass

if __name__ == '__main__':    
    
    try:
        main()
    except KeyboardInterrupt:
        if _bfs: _bfs.shutdown()
        if _parser: _parser.shutdown()
        if _cmdsvr: _cmdsvr.shutdown()
        if _wrwkr: _wrwkr.shutdown()
        if _email: _email.shutdown()
        if _emailchceck: _emailchceck.shutdown()
        if _btsvr: _btsvr.shutdown()        