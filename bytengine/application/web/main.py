from tornado import web
import json
import sqlite3
import os
import tempfile
import logging
import codecs
import uuid

from bytengine.application.core import sdk, common
from bytengine.application.core.routes import Route

#   Configure logging
formatter = logging.Formatter('%(asctime)-6s: %(name)s - %(levelname)s - %(message)s')
consoleLogger = logging.StreamHandler()
consoleLogger.setFormatter(formatter)
LOGGER = logging.getLogger(__name__)

# help database file
config_f = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
config_reader = json.load(open(config_f,"r"))
db_f = os.path.join(os.path.dirname(__file__),"..","core",config_reader["bytengine"]["help_database"])

NavBar = [
    {"name":"Home","url":"/ui"},{"name":"Terminal","url":"/ui/terminal"}, {"name":"IDE","url":"/ui/ide"},
    {"name":"Documentation","url":"/ui/documentation"},{"name":"Downloads","url":"/ui/downloads"}
]

@Route(r"/ui/?")
class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("main/index.html", page_title="Bytengine :: Home",navbar=None,
                    footer=False, page_keywords="",
                    page_description="Bytengine is a REST based data and digital content server that is designed to be scalable and developer friendly\
                                      It has a web based terminal (command line interface) as well as a file editor")

@Route(r"/ui/documentation")
class DocumentationIndexHandler(web.RequestHandler):
    def get(self):
        # get namespaces and commands
        conn = sqlite3.connect(db_f)
        cursor = conn.cursor()
        
        _query = "SELECT DISTINCT Namespace FROM tbl_help"
        cursor.execute(_query)
        rows = cursor.fetchall()        
        _help = {}
        for row in rows:
            _help[row[0]] = []
            
        _query = "SELECT Namespace, Command FROM tbl_help ORDER BY Namespace, Command"
        cursor.execute(_query)
        rows = cursor.fetchall()
        for row in rows:
            _nspace = row[0]
            _cmd = row[1]
            _help[_nspace].append(_cmd)
            
        cursor.close()

        self.render("main/documentation.html", page_title="Bytengine :: Documentation Home",
                    commands=_help, navbar=NavBar, navbar_active="Documentation", footer=True,
                    page_keywords="man, documentation, help", page_description="Bytengine documentation and help")

@Route(r"/ui/documentation/(\w+)/(\w+)")        
class DocumentationCommandHandler(web.RequestHandler):
    def get(self, namespace, command):
        # get namespaces and commands
        conn = sqlite3.connect(db_f)
        cursor = conn.cursor()
        
        _query = "SELECT DISTINCT Namespace FROM tbl_help"
        cursor.execute(_query)
        rows = cursor.fetchall()        
        _help = {}
        for row in rows:
            _help[row[0]] = []
            
        _query = "SELECT Namespace, Command FROM tbl_help ORDER BY Namespace, Command"
        cursor.execute(_query)
        rows = cursor.fetchall()
        for row in rows:
            _nspace = row[0]
            _cmd = row[1]
            _help[_nspace].append(_cmd)
        
        _query = "SELECT Namespace, Command, Help_Html FROM tbl_help WHERE Namespace=? AND Command=?"
        cursor.execute(_query,(namespace, command))
        row = cursor.fetchone()
        if row:
            self.render("main/command.html",
                        page_title="Bytengine :: Documentation", commands=_help, helptxt=row[2],
                        selected_namespace=row[0], selected_command=row[1],
                        navbar=NavBar, navbar_active="Documentation", footer=True,
                        page_keywords="help command linux bash", page_description="Bytengine help command: {}".format(command))
        else:
            self.set_status(404)
            self.write_error(404)
            
    def write_error(self, status_code, **kwargs):
        print status_code
        message_short = "Oops an error occured!"
        message_long = "The application has thrown an unhandled error. Please contact admin."
        if status_code == 404:
            message_short = "Oops! Page not found!"
            message_long="The page you've requested doesn't exist."
        elif status_code >= 500:
            message_short = "Oops an error occured!"
            message_long = "The application has thrown an unhandled error. Please contact admin."
        elif status_code == 405:
            message_short = "Oops an error occured!"
            message_long = "Http Method not allowed with this url."
        
        self.render("main/error.html",page_title="Bytengine :: Error",
                    error=status_code,message_short=message_short,
                    message_long=message_long, navbar=NavBar, navbar_active="", footer=True,
                    page_keywords="", page_description="Error Page")

@Route(r"/ui/terminal")            
class terminalHandler(web.RequestHandler):
    def get(self):
        self.render("main/terminal.html",page_title="Bytengine :: Terminal",
                    navbar=NavBar, navbar_active="Terminal", footer=False,
                    page_keywords="cli, terminal, bash", page_description="Bytengine Web Terminal or Command Line Interface")

@Route(r"/ui/downloads")        
class DownloadsHandler(web.RequestHandler):
    def get(self):
        self.render("main/downloads.html",
                        page_title="Bytengine :: Downloads", navbar=NavBar,
                        navbar_active="Downloads", footer=True,
                        page_keywords="connector clients, batch job, php client, python client",
                        page_description="Client connector Libraries and Other Developer Tools")

@Route(r"/ui/ide")        
class editorIndexHandler(web.RequestHandler):
    def get(self):
        self.render("main/ide.html",page_title="Bytengine :: IDE",
                    navbar=NavBar, navbar_active="IDE", footer=True,
                    page_keywords="editor, web ide, ide, code, coder", page_description="Bytengine online file and attachment Editor")

@Route(r"/ui/ide/load/file")        
class editorGetFileHandler(web.RequestHandler):
    def post(self):
        username = self.get_argument("username",default="")
        password = self.get_argument("password",default="")
        database = self.get_argument("database",default="")
        filepath = self.get_argument("filepath",default="")
        
        try:
            # login
            r = sdk.command_rpc("login -u='{}' -p='{}' -d='{}'".format(username, password, database))
            if not r["status"] == "ok":
                self.write("Authentication failure. Please check credentials.")
                self.set_status(401)
                return
            _session = r["data"]["ticket"]
            
            r = sdk.command_rpc('viewfile {}'.format(filepath), session=_session)            
            if not r["status"] == "ok":
                self.write(r["msg"])
                self.set_status(500)
            else:
                _formatted = json.dumps(r["data"]["content"],indent=2)
                self.set_header("Bytengine-IDE-Mode","json") 
                self.write(_formatted)
        except Exception, err:
            print err
            self.set_status(500)

@Route(r"/ui/ide/fileaccess")            
class editorSetFileAccessHandler(web.RequestHandler):
    def post(self):
        username = self.get_argument("username",default="")
        password = self.get_argument("password",default="")
        database = self.get_argument("database",default="")
        filepath = self.get_argument("filepath",default="")
        access = self.get_argument("access",default="private")
        
        try:
            # login
            r = sdk.command_rpc("login -u='{}' -p='{}' -d='{}'".format(username, password, database))
            if not r["status"] == "ok":
                self.write(common.ErrorResponse("Authentication failure. Please check credentials."))
                return
            _session = r["data"]["ticket"]
            
            if access == "public":
                r = sdk.command_rpc('mkpublic "{}"'.format(filepath), session=_session)            
                if not r["status"] == "ok":
                    self.write(r)
                    return
                else:
                    self.write(common.SuccessResponse("File access updated."))
            else:
                r = sdk.command_rpc('mkprivate "{}"'.format(filepath), session=_session)            
                if not r["status"] == "ok":
                    self.write(r)
                    return
                else:
                    self.write(common.SuccessResponse("File access updated."))
        except Exception, err:
            print err
            self.set_status(500)

@Route(r"/ui/ide/load/attachment")            
class editorGetAttachmentHandler(web.RequestHandler):
    def post(self):
        username = self.get_argument("username",default="")
        password = self.get_argument("password",default="")
        database = self.get_argument("database",default="")
        filepath = self.get_argument("filepath",default="")
        
        try:
            # login
            r = sdk.command_rpc("login -u='{}' -p='{}' -d='{}'".format(username, password, database))
            if not r["status"] == "ok":
                self.write("Authentication failure. Please check credentials.")
                self.set_status(401)
                return
            _session = r["data"]["ticket"]
            
            r = sdk.command_rpc('info {}'.format(filepath), session=_session)
            if r["status"] == "ok":
                if r["data"]["attachment"]:
                    _mime = r["data"]["mime"]
                    _ext = os.path.splitext(r["data"]["name"])[1]
                    _mode = getEditorMode(_mime,_ext)
                    if _mode == None:
                        self.write("File attachment can't be edited with the IDE")
                        self.set_status(500)
                        return
                    self.set_header("Bytengine-IDE-Mode",_mode)                    
                    r = sdk.command_rpc('download {}'.format(filepath), session=_session)
                    if r["status"] == "ok":
                        _pointer = "{}/{}/{}".format(config_reader["services"]["bfs"]["attachments_dir"],
                                                     r["data"]["database"],
                                                     r["data"]["file"])
                        # check size
                        _size = os.path.getsize(_pointer)
                        if _size > (1.0 * 1024 * 1000000):
                            self.write("File attachment is too large")
                            self.set_status(500)
                            return
                        
                        #_f = open(_pointer,"r")
                        #_data = _f.read()
                        #self.write(_data)
                        #return
                        _f = open(_pointer,"r")
                        for chunk in read_in_chunks(_f):
                            self.write(chunk)
                        return                       
            self.write("File attachment couldn't be retrieved")
            self.set_status(500)           
        except Exception, err:
            LOGGER.exception(err)
            self.set_status(500)

@Route(r"/ui/ide/save/file")            
class editorSaveFileHandler(web.RequestHandler):
    def post(self):
        data = self.get_argument("data",default="")
        username = self.get_argument("username",default="")
        password = self.get_argument("password",default="")
        database = self.get_argument("database",default="")
        filepath = self.get_argument("filepath",default="")
        
        try:
            # login
            r = sdk.command_rpc("login -u='{}' -p='{}' -d='{}'".format(username, password, database))
            if not r["status"] == "ok":
                self.write(common.ErrorResponse("Authentication failure. Please check credentials."))
                return
            _session = r["data"]["ticket"]
            
            r = sdk.command_rpc('modfile -o {} {}'.format(filepath, data), session=_session)
            if not r["status"] == "ok":
                self.write(r)
                return
            else:
                self.write(common.SuccessResponse("saved"))
        except Exception, err:
            print err
            self.write(common.ErrorResponse("save fail"))

@Route(r"/ui/ide/save/attachment")            
class editorSaveAttachmentHandler(web.RequestHandler):
    def post(self):
        data = self.get_argument("data",default="")
        username = self.get_argument("username",default="")
        password = self.get_argument("password",default="")
        database = self.get_argument("database",default="")
        filepath = self.get_argument("filepath",default="")
        data_source = self.get_argument("data_source",default="")
        
        try:
            # save file
            _path = "/tmp/attch_{}_tmp".format(uuid.uuid4().hex)
            file = codecs.open(_path, "w+", "utf-8")
            file.write(data)
            file.close()
            
            # login
            r = sdk.command_rpc("login -u='{}' -p='{}' -d='{}'".format(username, password, database))
            if not r["status"] == "ok":
                os.unlink(_path)
                self.write(common.ErrorResponse("Authentication failure. Please check credentials."))
                return
            _session = r["data"]["ticket"]
            
            r = sdk.command_rpc('upload {}'.format(filepath), session=_session, attachment=_path)
            if r["status"] == "ok":                
                self.write(common.SuccessResponse("saved"))
            else:
                self.write(common.ErrorResponse("save fail"))
        except Exception, err:
            LOGGER.exception(err)
            self.write(common.ErrorResponse("save fail"))

class siteErrorHandler(web.RequestHandler):
    def get(self):
        self.render("error.html",page_title="Bytengine | Error",
                    error="404",message_short="Oops! Page not found!",
                    message_long="The page you've requested doesn't exist.",
                    navbar=NavBar, navbar_active="", footer=False)
        
def getEditorMode(mime, file_extension):
    if mime in ["text/plain","application/x-empty","text/x-c"]:
        if file_extension in [".html",".htm"]:
            return "html"
        if file_extension == ".css":
            return "css"
        if file_extension == ".js":
            return "javascript"
        if file_extension in [".jinja",".tmpl"]:
            return "jinja2"
        return ""
    elif mime == "text/css":
        return "css"
    elif mime in ["text/html","application/template"]:
        return "html"
    elif mime in ["application/javascript","text/javascript"]:
        return "javascript"
    return None

def read_in_chunks(file_object, chunk_size=1024):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data