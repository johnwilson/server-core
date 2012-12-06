import cmd
import os
import requests
import shlex
import json
from connector import Connection

import logging

formatter = logging.Formatter('%(levelname)s - %(message)s')
consoleLogger = logging.StreamHandler()
consoleLogger.setFormatter(formatter)

LOGGER = logging.getLogger("bytengine.batchman")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(consoleLogger)

import argparse

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

class BytengineAdminConsole(cmd.Cmd):
    last_output = ''
    use_rawinput = False
    prompt = ""
    counter = 1
    connection = None

    def connect(self, address, port, username, password):
        self.connection = Connection(username, password, host=address, port=port)

    def parsecommand(self, line):
        command_parts = []
        try:
            lexer = shlex.shlex(line, posix=True)
            lexer.whitespace_split = True
            lexer.escapedquotes += "'"
            for token in lexer:
                command_parts.append(token)
            return command_parts
        except Exception, e:
            LOGGER.exception(e)
            return command_parts

    def emptyline(self):
        # do nothing
        pass

    def default(self, line):
        if line.startswith("#"): return
        reply = self.connection.command(line)
        self.displaySuccess(reply)

    def do_upload(self, line):
        parser = ModifiedOptionParser()
        parser.add_argument("-r","--remotepath",action="store", type=str)
        parser.add_argument("-l","--localpath",action="store", type=str)
        _parsed = parser.parse_args(self.parsecommand(line))
        _remote = _parsed.remotepath
        _local = _parsed.localpath
        reply = self.connection.uploadfile(_remote, _local)
        self.displaySuccess(reply)

    def do_download(self, line):
        parser = ModifiedOptionParser()
        parser.add_argument("-r","--remotepath",action="store", type=str)
        parser.add_argument("-l","--localpath",action="store", type=str)
        _parsed = parser.parse_args(self.parsecommand(line))
        _remote = _parsed.remotepath
        _local = _parsed.localpath
        reply = self.connection.downloadfile(_remote, _local)
        self.displaySuccess(reply)

    def postloop(self):
        self.ExitCLI()

    def preloop(self):
        pass

    def ExitCLI(self):
        print "Exiting ..."

    def do_EOF(self, line):
        print "\n"
        return True

    def displayError(self, message):
        LOGGER.error(message)

    def displaySuccess(self, message):
        if type(message) == dict or type(message) == list:
            message = json.dumps(message, indent=2)
        txt = "cmd:%s> ... %s" % (self.counter, message)
        self.counter +=1
        LOGGER.info(txt)

if __name__ == '__main__':
    batchman = None
    try:
        import sys

        parser = ModifiedOptionParser()
        parser.add_argument("batchfile",action="store", type=str)
        parser.add_argument("-u","--username",action="store", type=str)
        parser.add_argument("-p","--password",action="store", type=str)
        parser.add_argument("--address",action="store",default="127.0.0.1", type=str)
        parser.add_argument("--port",action="store",default=8500, type=int)
        _parsed = parser.parse_args()

        input = open(_parsed.batchfile, 'rt')
        batchman = BytengineAdminConsole(stdin=input)
        batchman.connect(_parsed.address, _parsed.port,
                         _parsed.username, _parsed.password)
        batchman.cmdloop()
    except Exception, err:
        LOGGER.exception(err)
        if batchman:
            batchman.ExitCLI()
