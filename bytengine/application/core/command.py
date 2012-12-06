import os
import sdk
import common
from common import CommandServer
from common import ModifiedOptionParser, OptionParsingError, OptionParsingExit
import sqlite3
from jinja2 import BaseLoader, TemplateNotFound, Environment, TemplateError
import re
import json
import types
import magic

class TemplateLoader(BaseLoader):
    def __init__(self, database):
        self.database = database

    def get_source(self, environment, template):
        _node = sdk.cmd_getnode_bypath(path=template,
                                       db=self.database,
                                       fields=["__header__"])
        if not _node:
            raise TemplateNotFound(template)
        if not "filepointer" in _node["__header__"]:
            raise TemplateNotFound(template)
        path = _node["__header__"]["filepointer"]
        if not os.path.exists(path):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(path)
        with file(path) as f:
            source = f.read().decode('utf-8')
        return source, path, lambda: mtime == os.path.getmtime(path)

class Server(CommandServer):
    def __init__(self, id, name="core", configfile=None):
        CommandServer.__init__(self, id, name, configfile)

        #-----------------------  Single Command Parser  --------------------------------
        self.psr_simplecmd = ModifiedOptionParser(add_help=False)
        self.psr_simplecmd.add_argument("command",action="store", type=str)
        
        #-----------------------  Email Status Check Parser  --------------------------------
        self.psr_emailstatus = ModifiedOptionParser(add_help=False)
        self.psr_emailstatus.add_argument("command",action="store", type=str)
        self.psr_emailstatus.add_argument("request_id",action="store", type=str)

        #-----------------------  Login Parser  --------------------------------
        self.psr_login = ModifiedOptionParser(add_help=False)
        self.psr_login.add_argument("command",action="store", type=str)
        self.psr_login.add_argument("-u","--username",action="store", type=str)
        self.psr_login.add_argument("-p","--password",action="store", type=str)
        self.psr_login.add_argument("-d","--database",action="store", type=str, default="")
        self.psr_login.add_argument("--usermode",action="store_true", default=False)

        #-----------------------  Logout Parser  --------------------------------
        self.psr_logout = ModifiedOptionParser(add_help=False)
        self.psr_logout.add_argument("command",action="store", type=str)
        self.psr_logout.add_argument("-u","--username",action="store", type=str)
        self.psr_logout.add_argument("-p","--password",action="store", type=str)

        #-----------------------  Makeuser Parser  -----------------------------
        self.psr_makeuser = ModifiedOptionParser(add_help=False)
        self.psr_makeuser.add_argument("command",action="store", type=str)
        self.psr_makeuser.add_argument("username",action="store", type=str, default="")
        self.psr_makeuser.add_argument("-p","--password",action="store", default="", type=str)

        #-----------------------  Readfile Parser  -----------------------------
        self.psr_readfile = ModifiedOptionParser(add_help=False)
        self.psr_readfile.add_argument("command",action="store", type=str)
        self.psr_readfile.add_argument("path",action="store", type=str)
        self.psr_readfile.add_argument("-f","--fields", nargs='*', dest='fields', default=[])

        #---------------------  Deleteuser Parser  -----------------------------
        self.psr_deleteuser = ModifiedOptionParser(add_help=False)
        self.psr_deleteuser.add_argument("command",action="store", type=str)
        self.psr_deleteuser.add_argument("username",action="store", type=str)

        #-----------------------  Getuser Parser  ------------------------------
        self.psr_getuser = ModifiedOptionParser(add_help=False)
        self.psr_getuser.add_argument("command",action="store", type=str)
        self.psr_getuser.add_argument("username",action="store", type=str)

        #-----------------------  Allusers Parser  -----------------------------
        self.psr_allusers = ModifiedOptionParser(add_help=False)
        self.psr_allusers.add_argument("command",action="store", type=str)

        #-----------------------  Password Parser  -----------------------------
        self.psr_password = ModifiedOptionParser(add_help=False)
        self.psr_password.add_argument("command",action="store", type=str)
        self.psr_password.add_argument("username",action="store", type=str)
        self.psr_password.add_argument("password",action="store", type=str)

        #-----------------------  Dbaccess Parser  -----------------------------
        self.psr_dbaccess = ModifiedOptionParser(add_help=False)
        self.psr_dbaccess.add_argument("command",action="store", type=str)
        self.psr_dbaccess.add_argument("username",action="store", type=str)
        self.psr_dbaccess.add_argument("database",action="store", type=str)
        group = self.psr_dbaccess.add_mutually_exclusive_group()
        group.add_argument("-r","--remove",action="store_true")
        group.add_argument("-a","--add",action="store_true")

        #-----------------------  Counter Parser  ------------------------------
        self.psr_counter_modify = ModifiedOptionParser(add_help=False)
        self.psr_counter_modify.add_argument("command", action="store")
        self.psr_counter_modify.add_argument("countername",action="store", type=str)
        subparsers = self.psr_counter_modify.add_subparsers()
        parser_1 = subparsers.add_parser("init")
        parser_1.add_argument("init",type=int,default=0,nargs="?")
        parser_2 = subparsers.add_parser("incr")
        parser_2.add_argument("incr",type=int,default=1,nargs="?")
        parser_3 = subparsers.add_parser("decr")
        parser_3.add_argument("decr",type=int,default=1,nargs="?")

        #-----------------------  Counter Get/Clear Parser  -----------------------------
        self.psr_counter = ModifiedOptionParser(add_help=False)
        self.psr_counter.add_argument("command", action="store")
        self.psr_counter.add_argument("countername",action="store", type=str)

        #-----------------------  Changedb Parser  -----------------------------
        self.psr_changedb = ModifiedOptionParser(add_help=False)
        self.psr_changedb.add_argument("command",action="store", type=str)
        self.psr_changedb.add_argument("dbname",action="store", type=str)

        #-----------------------  Whoami Parser  -----------------------------
        self.psr_whoami = ModifiedOptionParser(add_help=False)
        self.psr_whoami.add_argument("command",action="store", type=str)
        self.psr_whoami.add_argument("-a","--all",action="store_true", default=False)

        #-----------------------  Help Parser  -----------------------------
        self.psr_help = ModifiedOptionParser(add_help=False)
        self.psr_help.add_argument("command",action="store", type=str)
        self.psr_help.add_argument("helpcommand",action="store",nargs="?", default="*", type=str)
        self.psr_help.add_argument("-t","--text",action="store_true", default=False)
        self.psr_help.add_argument("-n","--namespace",action="store_true", default="core")

        #-----------------------  View Temlpate Parser  -----------------------------
        self.psr_templaterender = ModifiedOptionParser(add_help=False)
        self.psr_templaterender.add_argument("command",action="store", type=str)
        self.psr_templaterender.add_argument("path",action="store", type=str)
        self.psr_templaterender.add_argument("-d","--data",action="store", default=None)

        #-----------------------  Makedb Parser  -----------------------------
        self.psr_makedb = ModifiedOptionParser(add_help=False)
        self.psr_makedb.add_argument("command",action="store", type=str)
        self.psr_makedb.add_argument("dbname",action="store", type=str)

        #-----------------------  Copydb Parser  -----------------------------
        self.psr_copydb = ModifiedOptionParser(add_help=False)
        self.psr_copydb.add_argument("command",action="store", type=str)
        self.psr_copydb.add_argument("dbname",action="store", type=str)
        self.psr_copydb.add_argument("newdbname",action="store", type=str)

        #-----------------------  Dropdb Parser  -----------------------------
        self.psr_dropdb = ModifiedOptionParser(add_help=False)
        self.psr_dropdb.add_argument("command",action="store", type=str)
        self.psr_dropdb.add_argument("dbname",action="store", type=str)

        #-----------------------  Delete Parser  -----------------------------
        self.psr_delete = ModifiedOptionParser(add_help=False)
        self.psr_delete.add_argument("command",action="store", type=str)
        self.psr_delete.add_argument("paths", nargs='*', default=[])
        self.psr_delete.add_argument("-r","--recursive",action="store_true", default=False)

        #-----------------------  Rename Parser  -----------------------------
        self.psr_rename = ModifiedOptionParser(add_help=False)
        self.psr_rename.add_argument("command",action="store", type=str)
        self.psr_rename.add_argument("path",action="store", type=str)
        self.psr_rename.add_argument("name",action="store", type=str)

        #-----------------------  Move Parser  -----------------------------
        self.psr_move = ModifiedOptionParser(add_help=False)
        self.psr_move.add_argument("command",action="store", type=str)
        self.psr_move.add_argument("path",action="store", type=str)
        self.psr_move.add_argument("destination",action="store", type=str)
        self.psr_move.add_argument("-r","--rename",action="store", type=str)

        #----------------------- Copy  Parser  -----------------------------
        self.psr_copy = ModifiedOptionParser(add_help=False)
        self.psr_copy.add_argument("command",action="store", type=str)
        self.psr_copy.add_argument("path",action="store", type=str)
        self.psr_copy.add_argument("destination",action="store", type=str)
        self.psr_copy.add_argument("-r","--rename",action="store", type=str)

        #----------------------- GetPath (general)  Parser  -----------------------------
        self.psr_getpath = ModifiedOptionParser(add_help=False)
        self.psr_getpath.add_argument("command",action="store", type=str)
        self.psr_getpath.add_argument("path",action="store", type=str)

        #----------------------- Upload File  Parser  -----------------------------
        self.psr_uploadfile = ModifiedOptionParser(add_help=False)
        self.psr_uploadfile.add_argument("command",action="store", type=str)
        self.psr_uploadfile.add_argument("path",action="store", type=str)
        self.psr_uploadfile.add_argument("-m","--mime",action="store", type=str, default="")

        #-----------------------  Updatefile Parser  -----------------------------
        self.psr_updatefile = ModifiedOptionParser(add_help=False)
        self.psr_updatefile.add_argument("command",action="store", type=str)
        self.psr_updatefile.add_argument("path", action="store", type=str)
        self.psr_updatefile.add_argument("-o","--overwrite",action="store_true", default=False)

        #-----------------------  Set Value Parser  -----------------------------
        self.psr_setvalue = ModifiedOptionParser(add_help=False)
        self.psr_setvalue.add_argument("command",action="store", type=str)
        self.psr_setvalue.add_argument("paths", nargs="+", action="store", type=str)

        #-----------------------  Unset Value Parser  -----------------------------
        self.psr_unsetvalue = ModifiedOptionParser(add_help=False)
        self.psr_unsetvalue.add_argument("command",action="store", type=str)
        self.psr_unsetvalue.add_argument("paths", nargs="+", action="store", type=str)

        #----------------------- Directaccess  Parser  -----------------------------
        self.psr_directaccess = ModifiedOptionParser(add_help=False)
        self.psr_directaccess.add_argument("command",action="store", type=str)
        self.psr_directaccess.add_argument("database",action="store", type=str)
        self.psr_directaccess.add_argument("path",action="store", type=str)

        group = self.psr_directaccess.add_mutually_exclusive_group()
        group.add_argument("-j","--json",action="store_true")
        group.add_argument("-a","--attachment",action="store_true")

        #----------------------- Useraccess Parser  -----------------------------
        self.psr_useraccess = ModifiedOptionParser(add_help=False)
        self.psr_useraccess.add_argument("command",action="store", type=str)
        self.psr_useraccess.add_argument("username",action="store", type=str)

        group = self.psr_useraccess.add_mutually_exclusive_group()
        group.add_argument("-b","--block",action="store_true")
        group.add_argument("-a","--allow",action="store_true")

        #----------------------- Template Render Parser  -----------------------------
        self.psr_templaterender = ModifiedOptionParser(add_help=False)
        self.psr_templaterender.add_argument("command",action="store", type=str)
        self.psr_templaterender.add_argument("path",action="store", type=str)
        self.psr_templaterender.add_argument("-d","--data",action="append",
                                             dest="datafiles", default=[])

    #===========================================================================
    #   Helper functions
    #===========================================================================

    def validate_username(self, value):
        pattern = r"^[a-z]{1}([_]{0,1}[a-zA-Z0-9@.]{1,})+$"
        m = re.match(pattern,value)
        if not m:
            return None
        result = m.group()
        if result != value:
            return None
        return result

    def validate_dbname(self, value):
        pattern = r"^[a-z]{1}[a-z0-9_]{0,19}$"
        m = re.match(pattern,value)
        if not m:
            return None
        result = m.group()
        if result != value:
            return None
        return result

    def validate_filename(self, value):
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{1,}(.[a-zA-Z0-9]{1,6})+"
        m = re.match(pattern,value)
        if not m:
            return None
        result = m.group()
        if result != value:
            return None
        return result

    def validate_foldername(self, value):
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{1,}"
        m = re.match(pattern,value)
        if not m:
            return None
        result = m.group()
        if result != value:
            return None
        return result

    def __removetempfile(self, path):
        try:
            if os.path.exists(path) and os.path.isfile(path):
                os.unlink(path)
        except Exception, e:
            #Logger.exception(e)
            return False

    #===========================================================================
    #   User access command functions
    #===========================================================================

    def cmd_login(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** gives a user access to Bytengine server

        **SYNOPSIS**::

            {command} [-u username] [-p password] [-d database]

        **DESCRIPTION**:

        The **{command}** command allows authorized users to interact with Bytengine.
        It creates a session Id which should be included in subsequent Http 'POST'
        calls as the 'ticket' parameter.
        Bytengine has two 'interaction modes': **'User Mode'** and **'Application Mode'**
        **'Application Mode'** is the default mode used for software development whereas
        **'User Mode'** is used for administering your Bytengine account and allows
        switching of databases during the session. This is the default mode used
        by the **'Terminal Application'**.

        **Arguments**::

            -u, --username

            -p, --password

            -d, --database

        **Options**::

            --usermode  Add this option to interact with bytengine as a user

        **Examples**::

            {command} -u="guest" -p="p@55w0rd" -d="test"

            {command} -u="guest" --password="p@55w0rd" --usermode
        """

        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_login.parse_args(r["command"])
        pw = _parsed.password
        usr = _parsed.username
        db = _parsed.database
        if _parsed.usermode:
            usermode = "usermode"
        else:
            usermode = "appmode"

        root_name = self.configreader["general"]["admin"]
        root_pw = self.configreader["general"]["password"]
        if usr == root_name and pw == root_pw:
            ticket = sdk.cmd_createsession(username=usr, isroot=True, database=db, mode=usermode)
            if ticket:
                return common.SuccessResponse({"ticket":ticket}, command=_parsed.command)
            else:
                return common.INT_CommandError("Authentication failed")
        else:
            # authenticate user raises error on fail
            sdk.cmd_authenticate(username=usr,password=pw)

            ticket = sdk.cmd_createsession(username=usr, isroot=False, database=db, mode=usermode)
            if ticket:
                return common.SuccessResponse({"ticket":ticket}, command=_parsed.command)
            else:
                return common.INT_CommandError("Authentication failed")

    def cmd_logout(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** drop a Bytengine server user session

        **SYNOPSIS**::

            {command} [-u username] [-p password]

        **DESCRIPTION**:

        The **{command}** command ends the current **'User Mode'** session thereby
        making a slot available if the maximum number of allowed sessions is
        reached. This command will terminate a random session if a valid
        **'session id'** or **'ticket'** is not supplied.

        **Arguments**::

            -u, --username

            -p, --password

        **Options**:

        *None*

        **Examples**::

            {command} -u="guest" -p="p@55w0rd"
        """

        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_logout.parse_args(r["command"])
        pw = _parsed.password
        usr = _parsed.username

        root_name = self.configreader["general"]["admin"]
        root_pw = self.configreader["general"]["password"]
        if usr == root_name and pw == root_pw:
            reply = sdk.cmd_dropsession(username=usr, password=pw, ticket=sessionid)
        else:
            sdk.cmd_authenticate(username=usr,password=pw)
            reply = sdk.cmd_dropsession(username=usr, password=pw, ticket=sessionid)
        return common.SuccessResponse(reply, command=_parsed.command)

    def cmd_makeuser(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** creates a user account

        **SYNOPSIS**::

            {command} <username> [-p password]

        **DESCRIPTION**:

        The **{command}** command creates a Bytengine user account. *[username]*
        must start with a letter and should contain  only alpha-numeric characters
        as well as underscores and dashes. *[password]*, must be a minimum of 8
        characters.

        **Arguments**::

            username

            -p, --password

        **Options**:

        *None*

        **Examples**::

            {command} guest -p="p@55w0rd"

            {command} guest --password="p@55w0rd"
        """

        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_makeuser.parse_args(r["command"])
        pw = _parsed.password.strip()
        usr = _parsed.username.strip()

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")
        root_name = self.configreader["general"]["admin"]
        if usr == root_name:
            return common.INT_CommandError("invalid username")

        sdk.cmd_newuser(username=usr,password=pw)
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_deleteuser(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** removes user account from Bytengine.

        **SYNOPSIS**::

            {command} <username>

        **DESCRIPTION**:

        The **{command}** deletes a user account from Bytengine.

        **Arguments**::

            username    Use "*" to remove all users

        **Options**:

        *None*

        **Examples**::

            {command} "guest"
        """

        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_deleteuser.parse_args(r["command"])
        usr = _parsed.username.strip()

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")
        if usr == "*":
            sdk.cmd_removealluser()
        else:
            sdk.cmd_removeuser(username=usr)
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_getuser(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** retrieves user's details

        **SYNOPSIS**::

            {command} <username>

        **DESCRIPTION**:

        The **{command}** command retrieves a user's details.

        **Arguments**::

            username

        **Options**::

        *None*

        **Examples**::

            {command} guest
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getuser.parse_args(r["command"])
        usr = _parsed.username.strip()

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")
        _data = sdk.cmd_getuser(username=usr)
        return common.SuccessResponse(_data, command=_parsed.command)

    def cmd_allusers(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** list all user accounts

        **SYNOPSIS**::

            {command}

        **DESCRIPTION**:

        The **{command}** command lists all user accounts.

        **Arguments**:

        *None*

        **Options**:

        *None*

        **Examples**:

        *None*
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_allusers.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")

        _data = sdk.cmd_getalluser()
        return common.SuccessResponse(_data, command=_parsed.command)

    def cmd_password(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** update's user account password

        **SYNOPSIS**::

            {command} <username> <password>

        **DESCRIPTION**:

        The **{command}** command update's user account password.

        **Arguments**::

            username    Account to be updated

            password    New password

        **Options**:

        *None*

        **Examples**::

            {command} "guest" "p@55w0rd"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_password.parse_args(r["command"])
        pw = _parsed.password.strip()
        usr = _parsed.username.strip()

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")

        _data = sdk.cmd_updatepasswd(username=usr, password=pw)
        return common.SuccessResponse(_data, command=_parsed.command)

    def cmd_dbaccess(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** grant or revoke user's access to database.

        **SYNOPSIS**::

            {command} <username> <database> [-a -r]

        **DESCRIPTION**:

        The **{command}** command grants/revokes user access to database.

        **Arguments**::

            username

            database

        **Options**::

            -a, --add

            -r, --remove

        **Examples**::

            {command} "guest" "database1" -a

            {command} "guest" "database1" --remove
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_dbaccess.parse_args(r["command"])
        db = _parsed.database
        usr = _parsed.username

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")

        if _parsed.add:
            _data = sdk.cmd_grantdbaccess(database=db, username=usr)
            return common.SuccessResponse(_data, command=_parsed.command)
        elif _parsed.remove:
            _data = sdk.cmd_revokedbaccess(database=db, username=usr)
            return common.SuccessResponse(_data, command=_parsed.command)
        else:
            return common.INT_CommandError("invalid command format")

    def cmd_changedb(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** changes user's active database

        **SYNOPSIS**::

            {command} <database>

        **DESCRIPTION**:

        The **{command}** command changes the user's active database. This info
        will be stored in the session details.

        **Arguments**::

            database

        **Options**:

        *None*

        **Examples**::

            {command} test
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_changedb.parse_args(r["command"])
        db = _parsed.dbname

        alldbs = sdk.cmd_listdatabases()
        if not db in alldbs:
            return common.INT_CommandError("database not found")

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["mode"] == "usermode":
            return common.INT_CommandError("command only available in 'User Mode'")
        _usr = session["username"]
        if session["isroot"]:
            _hasaccess = True
        else:
            _hasaccess = sdk.cmd_hasdbaccess(username=_usr,database=db)

        if not _hasaccess:
            return common.INT_CommandError("current user doesn't have access rights to database: %s" % db)

        _updated = sdk.cmd_updatesession(ticket=sessionid, database=db)
        if not _updated:
            return common.INT_CommandError("database couldn't be changed")
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_currentdb(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** gets the current session database.

        **SYNOPSIS**::

            {command}

        **DESCRIPTION**:

        The **{command}** command gets the current session database name.

        **Arguments**:

        *None*

        **Options**:

        *None*

        **Examples**:

        *None*
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_simplecmd.parse_args(r["command"])
        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.SuccessResponse("", command=_parsed.command)
        return common.SuccessResponse(session["database"], command=_parsed.command)

    def cmd_whoami(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** displays current user

        **SYNOPSIS**::

            {command} [-a]

        **DESCRIPTION**:

        The **{command}** command displays the current session user's details.

        **Arguments**:

        *None*

        **Options**::

            -a, --all  Use this option to get full details

        **Examples**::

            {command} -all
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_whoami.parse_args(r["command"])
        getall = _parsed.all

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            if getall:
                _data = sdk.cmd_getuser(username=session["username"])
                # remove sensitive data
                del _data["password"]
                del _data["salt"]
                return common.SuccessResponse(_data, command=_parsed.command)
            else:
                return common.SuccessResponse(session["username"], command=_parsed.command)
        else:
            return common.SuccessResponse("root", command=_parsed.command)

    def cmd_useraccess(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** disable/enable user account

        **SYNOPSIS**::

            {command} <username> [-b -a]

        **DESCRIPTION**:

        The **{command}** command is used to disable/enable a user account's access
        to Bytengine.

        **Arguments**::

            username

        **Options**::

            -b, --block  Use this option to block user account

            -a, --allow  Use this option to unblock user account

        **Examples**::

            {command} "guest" -b

            {command} "guest" --allow
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_useraccess.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")

        usr = _parsed.username
        if _parsed.block:
            _result = sdk.cmd_deactivateuser(username=usr)
        elif _parsed.allow:
            _result = sdk.cmd_activateuser(username=usr)
        else:
            return common.INT_CommandError("invalid command format")
        return common.SuccessResponse(_result, command=_parsed.command)

    #===========================================================================
    #   Counter command functions
    #===========================================================================

    def cmd_counter(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** manages a 'counter' variable

        **SYNOPSIS**::

            {command} <counter> incr <value>

        Increments the specified counter. If counter doesn't exist a new one
        is created. If the 'value' isn't included the default value is '1'. ::

            {command} <counter> decr <value>

        Decrements the specified counter. If counter doesn't exist a new one
        is created. If the 'value' isn't included the default value is '1'. ::

            {command} <counter> init <value>

        Resets the specified counter. If counter doesn't exist a new one
        is created. If the 'value' isn't included the default value is '0'.
        'value' can be a negative value but remember to enclose it in quotes.

        **DESCRIPTION**:

        The **{command}** command creates and controls the value of a database level
        'global' variable called a **counter**. Counter values are integer types.
        A typical usage scenario would be to keep count of the number of veicles
        parked for example. This variable would therefore be available to any database
        level query.

        **Arguments**::

            counter     Name of the 'counter' variable

        **Options**:

        *None*

        **Examples**::

            {command} 'num_of_cars' incr 1

            {command} 'num_of_cars' decr

            {command} 'num_of_cars' init 10

            {command} 'temperature' init '-30'
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_counter_modify.parse_args(r["command"])
        countername = _parsed.countername

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        if "incr" in _parsed:
            r = sdk.cmd_counter_incr(db=db, counter=countername, value=_parsed.incr)
        elif "decr" in _parsed:
            r = sdk.cmd_counter_decr(db=db, counter=countername, value=_parsed.decr)
        elif "init" in _parsed:
            r = sdk.cmd_counter_init(db=db, counter=countername, value=_parsed.init)
        else:
            return common.INT_CommandError("Counter %s couldn't be updated" % countername)
        return common.SuccessResponse(r, command=_parsed.command)

    def cmd_counterlist(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** gets of all the current database's counters and their values

        **SYNOPSIS**::

            {command}

        **DESCRIPTION**:

        The **{command}** command gets of all the current database's counters
        and their values.

        **Arguments**:

        *None*

        **Options**:

        *None*

        **Examples**:

        *None*
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_simplecmd.parse_args(r["command"])
        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        r = sdk.cmd_counter_list(db=db)
        return common.SuccessResponse(r, command=_parsed.command)

    def cmd_counterclear(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** deletes the specified counter

        **SYNOPSIS**::

            {command} <counter>

        **DESCRIPTION**:

        The **{command}** command deletes the specified counter from the database.

        **Arguments**::

            counter

        **Options**:

        *None*

        **Examples**::

            {command} 'num_of_cars'
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_counter.parse_args(r["command"])
        countername = _parsed.countername

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        r = sdk.cmd_counter_clear(db=db, counter=countername)
        return common.SuccessResponse(r, command=_parsed.command)

    def cmd_counterinfo(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** retrieves the specified counter's current value

        **SYNOPSIS**::

            {command} <counter>

        **DESCRIPTION**:

        The **{command}** command retrieves the specified counter's current value.

        **Arguments**::

            counter

        **Options**:

        *None*

        **Examples**::

            {command} 'num_of_cars'
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_counter.parse_args(r["command"])
        countername = _parsed.countername

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        r = sdk.cmd_counter_get(db=db, counter=countername)
        return common.SuccessResponse(r, command=_parsed.command)

    #===========================================================================
    #   Server Management command functions
    #===========================================================================

    def cmd_alldbs(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** lists all databases in Bytengine

        **SYNOPSIS**::

            {command}

        **DESCRIPTION**:

        The **{command}** command lists all databases in Bytengine.

        **Arguments**:

        *None*

        **Options**:

        *None*

        **Examples**:

        *None*
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_simplecmd.parse_args(r["command"])
        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            _data = sdk.cmd_getuser(username=session["username"])["databases"]
        else:
            _data = sdk.cmd_listdatabases()
        return common.SuccessResponse(_data, command=_parsed.command)

    def cmd_initserver(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** rebuilds Bytengine server

        **SYNOPSIS**::

            {command}

        **DESCRIPTION**:

        The **{command}** command rebuilds Bytengine server.

        **Arguments**:

        *None*

        **Options**:

        *None*

        **Examples**:

        *None*
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_simplecmd.parse_args(r["command"])
        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")
        sdk.cmd_rebuildserver()
        sdk.cmd_removealluser()
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_makedb(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** creates a new database

        **SYNOPSIS**::

            {command} <database>

        **DESCRIPTION**:

        The **{command}** command creates a new database. Database name must
        start with a letter and can only contain a maximum of 20 alpha-numeric
        characters.

        **Arguments**::

            database

        **Options**:

        *None*

        **Examples**::

            {command} "test"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_makedb.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")

        db = _parsed.dbname
        valid_db = self.validate_dbname(db)
        if not db or db != valid_db:
            return common.INT_CommandError("database name isn't valid")
        result = sdk.cmd_makedatabase(db=db)
        if not result:
            return common.INT_CommandError("Command failed!")
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_copydb(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** gives a user access to Bytengine server

        **SYNOPSIS**::

            {command} <database1> <database2>

        **DESCRIPTION**:

        The **{command}** command creates a copy of an existing database and
        assigns it a new name. New database name must start with a letter and
        can only contain a maximum of 20 alpha-numeric characters.

        **Arguments**::

            database1   Database to be copied

            database2   New database name

        **Options**:

        *None*


        **Examples**::

            {command} "test" "test2"

        Creates a copy of database **test** and names it **test2**.
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_copydb.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")

        db = _parsed.dbname
        db_to = _parsed.newdbname

        valid_db = self.validate_dbname(db_to)
        if not db_to or db_to != valid_db:
            return common.INT_CommandError("new database name isn't valid")
        result = sdk.cmd_copydatabase(db_old=db, db_new=db_to)
        if not result:
            return common.INT_CommandError("Command failed!")
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_dropdb(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** deletes the database

        **SYNOPSIS**::

            {command} <database>

        **DESCRIPTION**:

        The **{command}** command deletes a database from Bytengine server.

        **Arguments**::

            database

        **Options**:

        *None*

        **Examples**::

            {command} "test"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_dropdb.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not session["isroot"]:
            return common.INT_CommandError("unauthorized command call")

        db = _parsed.dbname
        result = sdk.cmd_removedatabase(db=db)
        if not result:
            return common.INT_CommandError("database '%s' couldn't be deleted!" % db)
        return common.SuccessResponse("ok", command=_parsed.command)

    #===========================================================================
    #   Content Management command functions
    #===========================================================================

    def cmd_makedir(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** creates a new directory in the given path

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command creates a new directory in the given path.
        The name of the directory is the last in the path and all parent folders
        must already exist. Directory names must start with a letter and can
        contain alpha-numeric characters as well as underscores and dashes.

        **Arguments**::

            path   Path to the directory to be created

        **Options**:

        *None*

        **Examples**::

            {command} "/var/www/project1"

        Creates a directory named **'project1'** in the **'/var/www'** directory.
        The assumption here is that both **'/var'** and **'/var/www'** directories
        already exist.
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path.strip()

        parentdir, dirname = os.path.split(path)
        if len(parentdir) < 1:
            return common.INT_CommandError("parent directory not found.")

        valid_dirname = self.validate_foldername(dirname)
        if not valid_dirname:
            return common.INT_CommandError("Invalid directory name")

        # check if parent dir exists
        parentdir_node = sdk.cmd_getnode_bypath(path=parentdir,
                                                db=db,
                                                fields=["_id"])
        if not parentdir_node:
            return common.INT_CommandError("parent directory not found.")

        # check if content with same path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,
                                       fields=["_id"])
        if _node:
            return common.INT_CommandError("content with same name already exists.")

        # create new directory node
        _node = common.Directory()
        _node.name = valid_dirname
        _id = sdk.cmd_savenode(db=db,data=_node.serialize())
        if not _id:
            return common.INT_CommandError("Directory couldn't be created.")

        # add to parent directory
        isadded = sdk.cmd_addchild(db=db,
                                   parent_docId=str(parentdir_node["_id"]),
                                   child_docId = str(_id))
        if not isadded:
            # delete created directory
            return common.INT_CommandError("Directory couldn't be created.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_listdir(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** displays the content of the directory at the given path

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command displays the content of the directory at the
        given path. **{command}** will throw an error if the item at the given path
        isn't a directory.

        **Arguments**::

            path

        **Options**:

        *None*

        **Examples**::

            {command} "/var/www"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        path = _parsed.path

        # get item
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,
                                       fields=["__header__.name","__header__.type"])
        if not _node:
            return common.INT_CommandError("path not found.")

        # get child nodes
        _node_list = sdk.cmd_childnodes(docId=str(_node["_id"]),
                                        db=db,
                                        fields=["__header__"])
        result = {"afiles":[],"files":[],"dirs":[]}
        for item in _node_list:
            _name = item["__header__"]["name"]
            _type = item["__header__"]["type"]
            _hasattachment = False
            if "filepointer" in item["__header__"]:
                if not item["__header__"]["filepointer"] == "":
                    _hasattachment = True
            if _type == "Directory":
                result["dirs"].append(_name)
            elif _type == "File":
                if _hasattachment:
                    result["afiles"].append(_name)
                else:
                    result["files"].append(_name)

        return common.SuccessResponse(result, command=_parsed.command)

    def cmd_delete(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** deletes a directory or file at the given path

        **SYNOPSIS**::

            {command} <multiple_paths> [-r]

        **DESCRIPTION**:

        The **{command}** command deletes a directory or file at the given path.
        If item is a non-empty directory use '--recursive' or '-r' option to
        delete directory as well as all its contents.

        **Arguments**::

            multiple_paths  Space separated list of Files and/or Directories

        **Options**::

            -r, --recursive  Use this option to delete non-empty directories

        **Examples**::

            {command} "/tmp"

            {command} "/tmp/index.doc" "/tmp2"

            {command} "/tmp" -r
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_delete.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        paths = _parsed.paths
        isrecursive = _parsed.recursive

        # check if path exists
        for path in paths:
            _node = sdk.cmd_getnode_bypath(path=path,
                                           db=db,
                                           fields=["__header__.name","__header__.type"])
            if not _node:
                return common.INT_CommandError("path '{}' not found.".format(path))

            # check if is root dir
            _name = _node["__header__"]["name"]
            _type = _node["__header__"]["type"]

            if _name == "/" and _type == "Directory":
                return common.INT_CommandError("root directory cannot be deleted.")

            if _type == "Directory":
                #check if directory is empty
                dir_content = sdk.cmd_childnodes(docId=str(_node["_id"]),
                                                 db=db,fields=["_id"])
                if len(dir_content) > 0:
                    if not isrecursive:
                        return common.INT_CommandError("directory isn't empty. deletion failed.")
            isdeleted = sdk.cmd_removenode(docId=str(_node["_id"]),
                                           db=db)
            if not isdeleted:
                return common.INT_CommandError("directory couldn't be deleted.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_rename(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** renames a directory or file at the given path.

        **SYNOPSIS**::

            {command} <path> <name>

        **DESCRIPTION**:

        The **{command}** command renames a directory or file in the given path.
        This is on condition that an item with the same name as the new name
        doesn't already exist in the parent directory.

        **Arguments**::

            path    Path of the File or Directory

            name    New name

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp" "tmp2

            {command} "/tmp/index.doc" "index_copy.doc"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_rename.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        path = _parsed.path
        name = _parsed.name

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,
                                       fields=["__header__.name",
                                               "__header__.type",
                                               "__header__.parent"])
        if not _node:
            return common.INT_CommandError("path not found.")

        # check if is root dir
        _name = _node["__header__"]["name"]
        _type = _node["__header__"]["type"]

        if _name == "/" and _type == "Directory":
            return common.INT_CommandError("root directory cannot be renamed.")

        if _type == "Directory":
            name = self.validate_foldername(name)
            if not name:
                return common.INT_CommandError("invalid new directory name.")
        else:
            name = self.validate_filename(name)
            if not name:
                return common.INT_CommandError("invalid new file name.")

        # check if name is available
        # get child nodes
        _node_list = sdk.cmd_childnodes(docId=str(_node["__header__"]["parent"]),
                                        db=db,fields=["__header__.name"])
        for item in _node_list:
            if item["__header__"]["name"] == name:
                return common.INT_CommandError("item with same name already exists.")

        updated = sdk.cmd_updatenodes(query={"_id":_node["_id"]},
                                      updates={"$set":{"__header__.name":name}},
                                      db=db)
        if not updated:
            return common.INT_CommandError("rename failed.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_info(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** returns metadata about a file or directory at the given path

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command returns metadata about a file or directory at
        the given path. In the case of a File, details such as if it has any
        attachments will be shown.

        **Arguments**::

            path

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp"

            {command} "/tmp/index.doc"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__"])
        if not _node:
            return common.INT_CommandError("path not found.")

        # get child nodes
        _node_list = sdk.cmd_childnodes(docId=str(_node["_id"]),
                                        db=db,fields=["_id"])

        # remove sensitive data
        del _node["_id"]
        if "parent" in _node["__header__"]: del _node["__header__"]["parent"]
        _hasattachment = False
        if "filepointer" in _node["__header__"]:
            if not _node["__header__"]["filepointer"] == "":
                _hasattachment = True
            del _node["__header__"]["filepointer"]
        if _node["__header__"]["type"] == "Directory":
            _node["__header__"]["content count"] = len(_node_list)
            del _node["__header__"]["public"]
        elif _node["__header__"]["type"] == "File":
            _node["__header__"]["attachment"] = _hasattachment
        _node["__header__"]["created"] = str(_node["__header__"]["created"])

        return common.SuccessResponse(_node["__header__"], command=_parsed.command)

    def cmd_move(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** moves a directory or file at the given path to a new directory

        **SYNOPSIS**::

            {command} <current_path> <destination_directory> [-r]

        **DESCRIPTION**:

        The **{command}** command moves a directory or file in the given path to
        a new directory parent directory. This command will throw and error if
        an item with the same name already exists in the destination directory.
        If that is the case use the **'--rename'** option to avoid the name conflict
        error.

        **Arguments**::

            current_path

            destination_directory

        **Options**::

            -r, --rename  Use this option to avoid name conflict errors.

        **Examples**::

            {command} "/tmp" "/docs/"

        Moves file/directory **'tmp'** to directory **'/docs'**
        ::

            {command} "/tmp/index" "/docs/" -r="index_new.doc"

        Moves file **'/tmp/index'** to directory **'/docs'** and renames the
        file **'index'** to **'index_new.doc'**
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_move.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        path = _parsed.path
        to_path = _parsed.destination
        rename = _parsed.rename

        # check recursive move bug
        _srcpath = os.path.normpath(path)
        _topath = os.path.normpath(to_path)
        if _topath.find(_srcpath) == 0:
            return common.INT_CommandError("illegal move operation")

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__.name",
                                                     "__header__.type",
                                                     "__header__.parent"])
        _destination_node = sdk.cmd_getnode_bypath(path=to_path,
                                                   db=db,fields=["__header__.name",
                                                                 "__header__.type",
                                                                 "__header__.parent"])
        if not _node:
            return common.INT_CommandError("path not found.")
        if not _destination_node:
            return common.INT_CommandError("destination path not found.")
        if _destination_node["__header__"]["type"] != "Directory":
            return common.INT_CommandError("destination path must be a directory.")
        if _node["__header__"]["name"] == "/" and _node["__header__"]["type"] == "Directory":
            return common.INT_CommandError("root directory cannot be moved.")

        validated_name = None
        if rename:
            if _node["__header__"]["type"] == "Directory":
                validated_name = self.validate_foldername(rename)
            elif _node["__header__"]["type"] == "File":
                validated_name = self.validate_filename(rename)
            if not validate_filename:
                return common.INT_CommandError("invalid file/directory new name.")

        # check if name is available
        # get child nodes
        _node_list = sdk.cmd_childnodes(docId=str(_destination_node["_id"]),
                                        db=db,fields=["__header__.name"])

        if validated_name:
            for item in _node_list:
                if item["__header__"]["name"] == validated_name:
                    return common.INT_CommandError("item with same name already exists.")
        else:
            for item in _node_list:
                if item["__header__"]["name"] == _node["__header__"]["name"]:
                    return common.INT_CommandError("item with same name already exists.")

        result = sdk.cmd_addchild(parent_docId=str(_destination_node["_id"]),
                                  child_docId=str(_node["_id"]),
                                  db=db)
        if not result:
            return common.INT_CommandError("copy failed.")

        # rename copied node
        if validated_name:
            updated = sdk.cmd_updatenodes(query={"_id":_node["_id"]},
                                          updates={"$set":{"__header__.name":validated_name}},
                                          db=db)
            # if failed reverse action
            if not updated:
                return common.INT_CommandError("rename failed.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_copy(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** copies a directory or file at the given path to a new directory

        **SYNOPSIS**::

            {command} <current_path> <destination_directory> [-r]

        **DESCRIPTION**:

        The **{command}** command copies a directory or file in the given path to
        a new directory parent directory. This command will throw and error if
        an item with the same name already exists in the destination directory.
        If that is the case use the **'--rename'** option to avoid the name conflict
        error.

        **Arguments**::

            current_path

            destination_directory

        **Options**::

            -r, --rename  Use this option to avoid name conflict errors.

        **Examples**::

            {command} "/tmp" "/docs/"

        Copies file/directory **'tmp'** to directory **'/docs'**
        ::

            {command} "/tmp/index" "/docs/" -r="index_new.doc"

        Copies file **'/tmp/index'** to directory **'/docs'** and renames the
        file **'index'** to **'index_new.doc'**
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_copy.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path
        to_path = _parsed.destination
        rename = _parsed.rename

        # check recursive copy bug
        _srcpath = os.path.normpath(path)
        _topath = os.path.normpath(to_path)
        if _topath.find(_srcpath) == 0:
            return common.INT_CommandError("illegal copy operation")

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__.name",
                                                     "__header__.type",
                                                     "__header__.parent"])
        _destination_node = sdk.cmd_getnode_bypath(path=to_path,
                                                   db=db,fields=["__header__.name",
                                                                 "__header__.type",
                                                                 "__header__.parent"])
        if not _node:
            return common.INT_CommandError("path not found.")
        if not _destination_node:
            return common.INT_CommandError("destination path not found.")
        if _destination_node["__header__"]["type"] != "Directory":
            return common.INT_CommandError("destination path must be a directory.")
        if _node["__header__"]["name"] == "/" and _node["__header__"]["type"] == "Directory":
            return common.INT_CommandError("root directory cannot be copied.")

        validated_name = None
        if rename:
            if _node["__header__"]["type"] == "Directory":
                validated_name = self.validate_foldername(rename)
            elif _node["__header__"]["type"] == "File":
                validated_name = self.validate_filename(rename)
            if not validated_name:
                return common.INT_CommandError("invalid file/directory new name.")

        # check if name is available
        # get child nodes
        _node_list = sdk.cmd_childnodes(docId=str(_destination_node["_id"]),
                                        db=db,fields=["__header__.name"])
        if validated_name:
            for item in _node_list:
                if item["__header__"]["name"] == validated_name:
                    return common.INT_CommandError("item with same name already exists.")
        else:
            for item in _node_list:
                if item["__header__"]["name"] == _node["__header__"]["name"]:
                    return common.INT_CommandError("item with same name already exists.")

        result = sdk.cmd_copynode(parentId=str(_destination_node["_id"]),
                                  docId=str(_node["_id"]),
                                  db=db)
        if not result:
            return common.INT_CommandError("copy failed.")

        # rename copied node
        if validated_name:
            updated = sdk.cmd_updatenodes(query={"_id":result},
                                          updates={"$set":{"__header__.name":validated_name}},
                                          db=db)
            # if failed reverse action
            if not updated:
                return common.INT_CommandError("rename failed.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_makefile(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** creates a new file at the given path

        **SYNOPSIS**::

            {command} <path> <data>

        **DESCRIPTION**:

        The **{command}** command creates a new file in the given path.
        The File name must start with a letter and can contain alpha-numeric
        characters as well as underscores and dashes.
        Reserved top level JSON attribute are '_id' and '__header__'.

        **Arguments**::

            path    Path where the new File should be created

            data    File's JSON content.

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp/file" {{"name":{{"first":"michelle","last":"wilson"}}}}
        """
        r = sdk.cmd_parsecommandline_json(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path
        if "filedata" in r:
            if not len(r["filedata"]) > 0:
                jsondata = "{}"
            else:
                jsondata = r["filedata"].strip()
        else:
            return common.INT_CommandError("Check suspplied json data")

        parentdir, filename = os.path.split(path)
        if len(parentdir) < 1:
            return common.INT_CommandError("parent directory not found.")

        valid_filename = self.validate_filename(filename)
        if not valid_filename:
            return common.INT_CommandError("Invalid file name")

        # check if parent dir exists
        parentdir_node = sdk.cmd_getnode_bypath(path=parentdir,
                                                db=db,fields=["_id"])
        if not parentdir_node:
            return common.INT_CommandError("parent directory not found.")

        # check if content with same path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["_id"])
        if _node:
            return common.INT_CommandError("content with same name already exists.")

        # create new directory node
        _node = common.File()
        _node.name = valid_filename

        # check json data
        try:
            contentjson = json.loads(jsondata)
        except Exception, err:
            return common.INT_CommandError(str(err))

        # check json data for reserved names
        if "_id" in contentjson or "__header__" in contentjson:
            return common.INT_CommandError("File Json data contains reserved keywords.")
        _found = [k for k in contentjson.keys() if k.startswith("__header__.")]
        if len(_found) > 0:
            return common.INT_CommandError("Json data contains reserved keywords.")

        _node.content = contentjson
        _id = sdk.cmd_savenode(db=db,data=_node.serialize())
        if not _id:
            return common.INT_CommandError("File couldn't be created.")

        # add to parent directory
        isadded = sdk.cmd_addchild(db=db,
                                   parent_docId=str(parentdir_node["_id"]),
                                   child_docId = str(_id))
        if not isadded:
            # delete created file
            return common.INT_CommandError("Directory couldn't be created.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_readfile(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** reads the JSON content of File at the given path

        **SYNOPSIS**::

            {command} <path> [-f]

        **DESCRIPTION**:

        The **{command}** command reads the JSON content of File at the given path.

        **Arguments**::

            path

        **Options**::

            -f, --fields  List of fields to return. Ommit if all fields should be returned

        **Examples**::

            {command} "/tmp/file"

            {command} "/tmp/file" -f "age" "car.make"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_readfile.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path
        fields = _parsed.fields
        if not "__header__" in fields and not len(fields) == 0:
            fields.append("__header__")

        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=fields)
        if not _node:
            return common.INT_CommandError("path not found.")
        if _node["__header__"]["type"] != "File":
            return common.INT_CommandError("command only valid for files.")

        # remove header and id
        del _node["_id"]
        del _node["__header__"]

        return common.SuccessResponse({"path":path,"content":_node}, command=_parsed.command)

    def cmd_updatefile(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** updates File's JSON content with the submitted new data

        **SYNOPSIS**::

            {command} <path> <data> [-o]

        **DESCRIPTION**:

        The **{command}** command updates File's JSON content with the submitted
        new data. If **'--overwrite'** option is chosen new content will replace existing
        data else content will be updated. Matching attributes will be updated
        and new attributes will be added to the existing content.

        **Arguments**::

            path

            data    JSON data

        **Options**::

            -o, --overwrite  Use this option to replace existing json content

        **Examples**::

            {command} "/tmp/file" {{"user":"michelle"}}

            {command} "/tmp/file"  --overwrite {{"user":"michelle"}}
        """
        r = sdk.cmd_parsecommandline_json(command=commandline)
        _parsed = self.psr_updatefile.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path
        overwrite = _parsed.overwrite

        if "filedata" in r and len(r["filedata"]) > 0:
            jsondata = r["filedata"].strip()
        else:
            return common.INT_CommandError("Check suspplied json data")

        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=[])
        if not _node:
            return common.INT_CommandError("file not found.")
        if _node["__header__"]["type"] != "File":
            return common.INT_CommandError("command only valid for files.")

        # check json data
        try:
            contentjson = json.loads(jsondata)
        except Exception, err:
            return common.INT_CommandError(str(err))

        if "_id" in contentjson or "__header__" in contentjson:
            return common.INT_CommandError("Json data contains reserved keywords.")
        _found = [k for k in contentjson.keys() if k.startswith("__header__.")]
        if len(_found) > 0:
            return common.INT_CommandError("Json data contains reserved keywords.")

        _file = common.File(_node)
        if overwrite:
            _file.content = contentjson
        else:
            _file.content.update(contentjson)
        sdk.cmd_savenode(db=db,data=_file.serialize())

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_setvalue(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** updates a Group of Files' JSON content with the submitted new data

        **SYNOPSIS**::

            {command} <multiple_paths> <data>

        **DESCRIPTION**:

        The **{command}** command updates a group of Files' JSON content with the
        submitted new data (File Group Set). Matching attributes will be updated and new attributes
        will be added to the existing content.

        **Arguments**::

            multiple_paths  Space separated list of Files

            data            JSON data

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp/file" "/tmp/subdir/file2 {{"owner":"francois"}}
        """
        r = sdk.cmd_parsecommandline_json(command=commandline)
        _parsed = self.psr_setvalue.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        paths = _parsed.paths

        if "filedata" in r and len(r["filedata"]) > 0:
            jsondata = r["filedata"].strip()
        else:
            return common.INT_CommandError("Check suspplied json data")

        _node_list = []
        for path in paths:
            _node = sdk.cmd_getnode_bypath(path=path, db=db,fields=[])
            if not _node:
                return common.INT_CommandError("'{0}' not found.".format(path))
            if _node["__header__"]["type"] != "File":
                return common.INT_CommandError("'{0}' isn't a file.".format(path))
            _node_list.append(_node["_id"])

        # check json data
        try:
            contentjson = json.loads(jsondata)
        except Exception, err:
            return common.INT_CommandError(str(err))

        if "_id" in contentjson or "__header__" in contentjson:
            return common.INT_CommandError("Json data contains reserved keywords.")
        # second keyword test
        _found = [k for k in contentjson.keys() if k.startswith("__header__.")]
        if len(_found) > 0:
            return common.INT_CommandError("Json data contains reserved keywords.")

        query = {"_id":{"$in":_node_list}}
        updates = {"$set":contentjson}
        sdk.cmd_updatenodes(db=db, query=query, updates=updates)
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_unsetvalue(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** removes a Group of Files' JSON content.

        **SYNOPSIS**::

            {command} <multiple_paths> <data>

        **DESCRIPTION**:

        The **{command}** command removes a group of Files' JSON content. The data
        submitted should be an array of JSON 'attributes' to be deleted.

        **Arguments**::

            multiple_paths  Space separated list of Files

            data            JSON array

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp/file" "/tmp/subdir/file2 ["owner","title"]
        """
        r = sdk.cmd_parsecommandline_json(command=commandline)
        _parsed = self.psr_unsetvalue.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        paths = _parsed.paths

        if "filedata" in r and len(r["filedata"]) > 0:
            jsondata = r["filedata"].strip()
        else:
            return common.INT_CommandError("Check suspplied json data")

        _node_list = []
        for path in paths:
            _node = sdk.cmd_getnode_bypath(path=path, db=db,fields=[])
            if not _node:
                return common.INT_CommandError("'{0}' not found.".format(path))
            if _node["__header__"]["type"] != "File":
                return common.INT_CommandError("'{0}' isn't a file.".format(path))
            _node_list.append(_node["_id"])

        # check json data
        try:
            contentjson = json.loads(jsondata)
            assert type(contentjson) is types.ListType
        except AssertionError, err:
            return common.INT_CommandError(u"JSON data must be an array of 'attributes'")
        except Exception, err:
            return common.INT_CommandError(str(err))

        if "_id" in contentjson or "__header__" in contentjson:
            return common.INT_CommandError("Json data contains reserved keywords.")
        _found = [k for k in contentjson if k.startswith("__header__.")]
        if len(_found) > 0:
            return common.INT_CommandError("Json data contains reserved keywords.")

        query = {"_id":{"$in":_node_list}}
        updates = {"$unset":{}}
        for field in contentjson:
            if type(field) in types.StringTypes:
                if field.startswith("__header__.") or field == "__header__" or field == "_id":
                    continue
                updates["$unset"][field] = 1
        sdk.cmd_updatenodes(db=db, query=query, updates=updates)
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_makepublic(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** makes a File's content and attachment available via Http GET

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command makes a File's content and attachment directly
        available without authentication using Http GET. This allows developers
        to serve for example images directly from Bytengine to their html <img> tags.

        The File's JSON content and attachment can be accessed from the following urls:

        **JSON data**: http://<host>:<port>/direct/fd/<database>/<filepath>

        **Attachment**: http://<host>:<port>/direct/fa/<database>/<filepath>

        **Arguments**::

            path

        **Options**:

        *None*

        **Examples**::

            {command} "/holidays/picture1"

        The above File's attachment would therefore be accessible from the following url:
        http://<host>:<port>/direct/fa/<database>/holidays/picture1
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__.name",
                                                     "__header__.type",
                                                     "__header__.parent"])
        if not _node:
            return common.INT_CommandError("path not found.")

        if _node["__header__"]["type"] != "File":
            return common.INT_CommandError("Command only valid for files.")

        updated = sdk.cmd_updatenodes(query={"_id":_node["_id"]},
                                      updates={"$set":{"__header__.public":True}},
                                      db=db,)
        if not updated:
            return common.INT_CommandError("make public failed.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_makeprivate(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** disables direct access to a File's content and attachment

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command disables direct access a File's content and
        attachment directly using Http GET. Direct access would normally allow
        developers to serve for example images directly from Bytengine to their
        html <img> tags.

        **Arguments**::

            path

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp/file"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__.name",
                                                     "__header__.type",
                                                     "__header__.parent"])
        if not _node:
            return common.INT_CommandError("path not found.")

        if _node["__header__"]["type"] != "File":
            return common.INT_CommandError("Command only valid for files.")

        updated = sdk.cmd_updatenodes(query={"_id":_node["_id"]},
                                      updates={"$set":{"__header__.public":False}},
                                      db=db)
        if not updated:
            return common.INT_CommandError("make public failed.")

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_upload(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** uploads an attachment to a Bytengine File at the given path

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command uploads an attachment to a Bytengine File at
        the given path. The File must already exist in the database.
        **{command}** requires a multi-part Http Form POST be done with a **'file'**
        parameter representing the remote file to be uploaded.

        **Arguments**::

            path    Path to File on Bytengine to which attachment should be uploaded

        **Options**::

            -m, --mime  Add file mime type.

        *None*

        **Examples**::

            {command} "/tmp/picture1.png"

            {command} "/tmp/picture2" -m="image/jpeg"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_uploadfile.parse_args(r["command"])

        try:
            session = sdk.cmd_getsession(ticket=sessionid)
        except common.BytengineError, err:
            self.__removetempfile(attachmentpath)
            raise

        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__.name",
                                                     "__header__.type",
                                                     "__header__.filepointer"])
        if not _node:
            self.__removetempfile(attachmentpath)
            return common.INT_CommandError("path not found.")

        if _node["__header__"]["type"] != "File":
            self.__removetempfile(attachmentpath)
            return common.INT_CommandError("Command only valid for files.")

        # remove existing attachment if any
        _old_attchment = _node["__header__"]["filepointer"]
        if len(_old_attchment) > 0:
            sdk.cmd_removeattachment(path=_old_attchment)

        # copy from tmp location to attachments
        _filepointer = sdk.cmd_saveattachment(path=attachmentpath,
                                              db=db)
        if not _filepointer:
            self.__removetempfile(attachmentpath)
            return common.INT_CommandError("upload attachment failed.")

        # file size
        _size = os.path.getsize(_filepointer)
        # get mime type
        _mime = _parsed.mime
        try:
            if _mime == "":
                _extension = os.path.splitext(_node["__header__"]["name"])[1]
                print _extension
                _mimelist = common.GetMimeList()
                if not _extension in _mimelist:
                    # guess
                    _f = open(_filepointer)
                    _mime = magic.from_buffer(_f.read(1024), mime=True)
                    _f.close()
                else:
                    _mime = _mimelist[_extension]
        except:
            _mime = "application/octet-stream"
        updated = sdk.cmd_updatenodes(query={"_id":_node["_id"]},
                                      updates={"$set":{"__header__.filepointer":_filepointer,
                                                       "__header__.size":_size,
                                                       "__header__.mime":_mime}},
                                      db=db)
        if not updated:
            self.__removetempfile(attachmentpath)
            return common.INT_CommandError("upload attachment failed.")

        self.__removetempfile(attachmentpath)
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_directaccess(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** retrieves the contents of a File marked as public

        **SYNOPSIS**::

            {command} <database> <path> [-j -a]

        **DESCRIPTION**:

        The **{command}** command retrieves the contents of a File marked as public.
        This is an internal Bytengine command. Developers should use the direct
        access Http GET urls.

        **Arguments**::

            database

            path

        **Options**::

            -j, --json  Use this option to get json content

            -a, --attachment  Use this option to get attachment

        **Examples**::

            {command} "test" "/tmp/file" -j

            {command} "test" "/tmp/file" -a
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_directaccess.parse_args(r["command"])

        path = _parsed.path
        database = _parsed.database

        if not database in sdk.cmd_listdatabases():
            return common.INT_CommandError("database '%s' doesn't exist" % database)

        if _parsed.json:
            _node = sdk.cmd_getnode_bypath(path=path,
                                           db=database,
                                           fields=[])
            if not _node:
                return common.INT_CommandError("directAccessJson: node not found")
            if _node["__header__"]["type"] != "File":
                return common.INT_CommandError("directAccessJson: path not file")
            if _node["__header__"]["public"] != True:
                return common.INT_CommandError("directAccessJson: file not public")
            # remove header and id
            del _node["_id"]
            del _node["__header__"]
            return common.SuccessResponse(_node, command=_parsed.command)
        elif _parsed.attachment:
            _node = sdk.cmd_getnode_bypath(path=path,
                                           db=database,
                                           fields=["__header__"])
            if not _node:
                raise common.INT_CommandError("directAccessJson: node not found")
            if _node["__header__"]["type"] != "File":
                raise common.INT_CommandError("directAccessJson: path not file")
            if _node["__header__"]["public"] != True:
                raise common.INT_CommandError("directAccessJson: file not public")
            _extension = os.path.splitext(path)[1]

            _attachment = _node["__header__"]["filepointer"]
            if not os.path.exists(_attachment):
                raise common.INT_CommandError("directAccessJson: attachment not found")
            if "mime" in _node["__header__"]:
                _mime = _node["__header__"]["mime"]
            else:
                _mime = "application/octet-stream"
            _data = {"database":database,
                     "attachment":_attachment,
                     "mime":_mime,
                     "extension":_extension,
                     "filename":_node["__header__"]["name"]}
            return common.SuccessResponse(_data, command=_parsed.command)

        return common.INT_CommandError("data not found")

    def cmd_download(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** downloads a File's attachment if it's not marked as 'public'

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command downloads a File's attachment if it's not marked
        as 'public'. The extension given to the File will be used to set the
        Http content-type. If content type cannot be determined it will default to
        **'application/octet-stream'**.

        **Arguments**::

            path

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp/file"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path

        if not db in sdk.cmd_listdatabases():
            return common.INT_CommandError("database '%s' doesn't exist" % db)

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__.name",
                                                     "__header__.type",
                                                     "__header__.filepointer"])
        if not _node:
            return common.INT_CommandError("path not found.")

        if _node["__header__"]["type"] != "File":
            return common.INT_CommandError("Command only valid for files.")

        _filepointer = _node["__header__"]["filepointer"]
        if not os.path.exists(_filepointer):
            return common.INT_CommandError("No attachment found.")
        if "mime" in _node["__header__"]:
            _mime = _node["__header__"]["mime"]
        else:
            _mime = "application/octet-stream"
        _data = {"database":db,
                 "mime":_mime,
                 "file":os.path.basename(_filepointer)}
        return common.SuccessResponse(_data, command=_parsed.command)

    def cmd_rmattachment(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** deletes the File's attachment

        **SYNOPSIS**::

            {command} <path>

        **DESCRIPTION**:

        The **{command}** command deletes the File's attachment.

        **Arguments**::

            path Path to the File

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp/index.doc"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_getpath.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        path = _parsed.path

        # check if path exists
        _node = sdk.cmd_getnode_bypath(path=path,
                                       db=db,fields=["__header__.name",
                                                     "__header__.type",
                                                     "__header__.filepointer"])
        if not _node:
            return common.INT_CommandError("path not found.")

        if _node["__header__"]["type"] != "File":
            return common.INT_CommandError("Command only valid for files.")

        # remove existing attachment if any
        sdk.cmd_removeattachment(path=_node["__header__"]["filepointer"])
        # remove node's file pointer
        sdk.cmd_updatenodes(query={"_id":_node["_id"]}, updates={"$set":{"__header__.filepointer":""}}, db=db)

        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_mongoupdate(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** updates a Group of Files' JSON content using the submitted pymongo query

        **SYNOPSIS**::

            {command} <multiple_paths> <update_query>

        **DESCRIPTION**:

        The **{command}** command updates a group of Files' JSON content with the
        submitted **pymongo** query. **Use this command with care**. Pymongo queries
        are based on mongodb queries so refer to 'mongodb update' documentation for
        more information.

        **Arguments**::

            multiple_paths  Space separated list of Files

            update_query    Pymongo JSON format query

        **Options**:

        *None*

        **Examples**::

            {command} "/tmp/file" "/tmp/subdir/file2" {{"$set":{{"user.age":32}}}}
        """
        r = sdk.cmd_parsecommandline_json(command=commandline)
        _parsed = self.psr_setvalue.parse_args(r["command"])

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]
        paths = _parsed.paths

        if "filedata" in r and len(r["filedata"]) > 0:
            jsondata = r["filedata"].strip()
        else:
            return common.INT_CommandError("Check suspplied json data")

        _node_list = []
        for path in paths:
            _node = sdk.cmd_getnode_bypath(path=path, db=db,fields=[])
            if not _node:
                return common.INT_CommandError("'{0}' not found.".format(path))
            if _node["__header__"]["type"] != "File":
                return common.INT_CommandError("'{0}' isn't a file.".format(path))
            _node_list.append(_node["_id"])

        # check json data
        try:
            contentjson = json.loads(jsondata)
        except Exception, err:
            return common.INT_CommandError(str(err))

        for _cmd in contentjson:
            item = contentjson[_cmd]
            if "_id" in item or "__header__" in item:
                return common.INT_CommandError("Json data contains reserved keywords.")
            # second keyword test
            _found = [k for k in item.keys() if k.startswith("__header__.")]
            if len(_found) > 0:
                return common.INT_CommandError("Json data contains reserved keywords.")

        query = {"_id":{"$in":_node_list}}
        sdk.cmd_updatenodes(db=db, query=query, updates=contentjson)
        return common.SuccessResponse("ok", command=_parsed.command)

    def cmd_find(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** uses Bytengine Query Language (BQL) to retrieve Files

        **SYNOPSIS**::

            {command} <query>

        **DESCRIPTION**:

        The **{command}** command uses Bytengine Query Language (BQL) to retrieve
        File JSON data from Bytengine. View the BQL documentation for language
        specifications.

        **Arguments**::

            query   BQL query

        **Options**:

        *None*

        **Examples**::

            {command} Select ("name","age") From ("/tmp/users") Where $eq("age",56) AND $gt("balance",30000)

            {command} Select ("make") From ("/cars") Where $eq("color","blue") OR $equal("color","red")

            {command} Select ("make") From ("/cars") Where $in("color",["blue","red"]) Limit(50)

            {command} Select ("name") From ("/students") Asc("firstname","age")

            {command} Select ("name") From ("/students") Where $eq("academic_year",2) Desc("grade")

            {command} Select ("country") From ("/outbound_calls") Where $gt("duration_in_hours",1) Distinct("country")


        **Bytengine Query Language**

        Queries are in the form of:

        **Select** (<Fields>) **From** (<Directories>) **Where** <Conditions> Distinct|Limit|Sort

        Where Conditions::

            Data types:
            ===========

            $double(<Field>)      Where <Field> is of data type 'double'.
            $string(<Field>)      Where <Field> is of data type 'string'.
            $array(<Field>)       Where <Field> is of data type 'array'.
            $bool(<Field>)        Where <Field> is of data type 'bool'.
            $date(<Field>)        Where <Field> is of data type 'date'.
            $int32(<Field>)       Where <Field> is of data type 'int32'.
            $int(<Field>)         Where <Field> is of data type 'int'.
            $object(<Field>)      Where <Field> is of data type 'JSON object'.

            Availability:
            =============

            $exists(<Field>)       Where <Field> Exist in JSON object.
            $nexists(<Field>)      Where <Field> Doesn't exist in JSON object.

            Comparison:
            ===========

            $eq(<Field>,<Value>)    Where <Field> is Equal to <Value>.
            $neq(<Field>,<Value>)   Where <Field> is Not Equal to <Value>.
            $lt(<Field>,<Value>)    Where <Field> is Less Than <Value>.
            $gt(<Field>,<Value>)    Where <Field> is Greater Than <Value>.
            $lte(<Field>,<Value>)   Where <Field> is Less Than or Equal to <Value>.
            $gte(<Field>,<Value>)   Where <Field> is Greater Than or Equal to <Value>.
            $regex(<Field>,<Value>) Where Regular Expression <Value> matches <Field>.

            Inclusion:
            ==========

            $in(<Field>,[<Value_1>,...,<Value_n>])    Where <Field> is one of the values in the list.
            $nin(<Field>,[<Value_1>,...,<Value_n>])    Where <Field> is not one of the values in the list.

        Resultset Management::

            Limit(<Value>)  Number of records to return. <Value> is an integer
            Asc(<Field_1>,...,<Field_n>)   Sort Fields Ascending
            Desc(<Field_1>,...,<Field_n>)   Sort Fields Descending
            Distinct([<Field_1>,...,<Field_n>])   Distinct Values for Fields
        """
        #retrieve select query
        _cmdparts = commandline.split(None,1)
        if len(_cmdparts) < 2:
            return common.INT_CommandError("Invalid query format.")

        query = _cmdparts[1].lstrip()

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        r = sdk.cmd_find(query=query, db=db)
        return common.SuccessResponse(r, command=_cmdparts[0].strip())

    #===========================================================================
    #   View Templates command functions
    #===========================================================================

    def cmd_templaterender(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** makes use of Bytengine's templating services

        **SYNOPSIS**::

            {command} <path> [-d] <data>

        **DESCRIPTION**:

        The **{command}** command makes use of Bytengine's templating services to
        render text using File JSON content. The template language is based on
        Jinja2. The template file should be saved as a Bytengine File attachment
        whose JSON content will be used as the the template's data source as well
        as any embedded JSON data in the command. Additional JSON data can be sourcesd
        from different Files by using the the **'-d'** option.

        **Arguments**::

            path    Template File path

            data    Embedded JSON content.

        **Options**::

            -d, --data  Path to additinal JSON data source Files

        **Examples**::

            {command} "/var/www/template1" {{"name":"Clark Kent"}}

            {command} "/var/www/template1" -d="/datafile1" -d="/datafile2" {{"name":"Clark Kent"}}
        """
        r = sdk.cmd_parsecommandline_json(command=commandline)
        _parsed = self.psr_templaterender.parse_args(r["command"])

        path = _parsed.path
        _datafiles = _parsed.datafiles

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        if "filedata" in r:
            if not len(r["filedata"]) > 0:
                jsondata = "{}"
            else:
                jsondata = r["filedata"].strip()
        else:
            return common.INT_CommandError("Check embedded json data")

        # check json data
        try:
            contentjson = json.loads(jsondata)
        except Exception, err:
            return common.INT_CommandError(str(err))

        try:
            loader = TemplateLoader(db)
            env = Environment(loader=loader,auto_reload=False)
            _template = env.get_template(path)
            _finaldata = {}
            # add embedded JSON
            _finaldata.update(contentjson)

            # add template file JSON
            t_node = sdk.cmd_getnode_bypath(path=path, db=db, fields=[])
            if not t_node:
                return common.INT_CommandError("Template data file not found")
            del t_node["__header__"]
            _finaldata.update(t_node)

            for item in _datafiles:
                _node = sdk.cmd_getnode_bypath(path=item, db=db, fields=[])
                if not _node:
                    return common.INT_CommandError("Additional data file {} not found".format(item))
                del _node["__header__"]
                _finaldata.update(_node)
            _render = _template.render(**_finaldata)

            return common.SuccessResponse(_render, command=_parsed.command)
        except TemplateNotFound, e:
            return common.INT_CommandError("Template not found")
        except TemplateError, e:
            return common.INT_CommandError(e.message)

    #===========================================================================
    #   Help command functions
    #===========================================================================

    def cmd_help(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** Bytengine help

        **SYNOPSIS**::

            {command} <command> [-n -t]

        **DESCRIPTION**:

        The **{command}** command displays Bytengine's command documentation.

        **Arguments**::

            command Name of command. Leave blank to get a list of all commands.

        **Options**::

            -n, --namespace  Adds namespace to filter command (default namespace is "core")

            -t, --text  Retrieves help in text format (default format is Html)

        **Examples**::

            help

        Gets a list of all Bytengine server commands
        ::

            help login

            help makefile -t

            help plotgraph --n="my_command_namespace"
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_help.parse_args(r["command"])
        helpcommand = _parsed.helpcommand
        returntext = _parsed.text
        namespace = _parsed.namespace

        db_f = os.path.join(os.path.dirname(__file__),self.configreader["bytengine"]["help_database"])
        conn = sqlite3.connect(db_f)
        cursor = conn.cursor()

        if helpcommand == "*":
            _query = "SELECT Namespace, Command FROM tbl_help ORDER BY Namespace, Command"
            cursor.execute(_query)
            rows = cursor.fetchall()
            _result = {}
            for row in rows:
                if row[0] not in _result:
                    _result[row[0]]=[]
                _result[row[0]].append(row[1])
            return common.SuccessResponse(_result, command="help *")
        else:
            _query = "SELECT * FROM tbl_help WHERE Namespace=? AND Command=?"
            param = (namespace,helpcommand)
            cursor.execute(_query,param)
            row = cursor.fetchone()
            if not row:
                return common.INT_CommandError("command not found")
            if returntext:
                cmdhelp = row[3]
            else:
                cmdhelp = row[4]
            return common.SuccessResponse(cmdhelp, command=_parsed.command)
        
    #===========================================================================
    #   Email command functions
    #===========================================================================

    def cmd_emailsend(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** sends a plain text email

        **SYNOPSIS**::

            {command} <path> [-d] <data>

        **DESCRIPTION**:

        The **{command}** command sends a plain text email using Bytengine's
        templating services to render the email content. View the template
        creation command for more details.
        The **embedded JSON data** in the command must follow the format bellow::
        
            {{
                "smtp":{{
                    "subject":"test",
                    "to":["user1@nomail.com","user2@nomail.com","..."],
                    "from":"me@nomail.com",
                    "author":"Me",
                    "mailserver":"smtp.gmail.com:587",
                    "password":"1234567"
                }}
            }}
        
        **Arguments**::

            path    Email content Template File path

            data    Embedded JSON data.

        **Options**::

            -d, --data  Path to additinal JSON data source Files

        **Examples**::

            {command} "/var/www/template1" {{"name":"Mr Clark Kent", "smtp":{{ ... }}}}

            {command} "/var/www/template1" -d="/datafile1" -d="/datafile2" {{"name":"Mr Clark Kent", "smtp":{{ ... }}}}
        """
        r = sdk.cmd_parsecommandline_json(command=commandline)
        _parsed = self.psr_templaterender.parse_args(r["command"])

        path = _parsed.path
        _datafiles = _parsed.datafiles

        session = sdk.cmd_getsession(ticket=sessionid)
        if not "database" in session:
            return common.INT_CommandError("database not selected")
        db = session["database"]

        if "filedata" in r:
            if not len(r["filedata"]) > 0:
                jsondata = "{}"
            else:
                jsondata = r["filedata"].strip()
        else:
            return common.INT_CommandError("Check embedded json data")

        # check json data
        try:
            contentjson = json.loads(jsondata)
            if not "smtp" in contentjson:
                raise Exception("SMTP information missing")
            assert type(contentjson["smtp"]) is types.DictType, "SMTP data format is invalid"            
        except Exception, err:
            return common.INT_CommandError(str(err))

        try:
            loader = TemplateLoader(db)
            env = Environment(loader=loader,auto_reload=False)
            _template = env.get_template(path)
            
            _finaldata = {}
            
            # process embedded JSON
            _smtp = contentjson.pop("smtp")
            _finaldata.update(contentjson)
            
            # get template file JSON
            t_node = sdk.cmd_getnode_bypath(path=path, db=db, fields=[])
            if not t_node:
                return common.INT_CommandError("Template data file not found")
            del t_node["__header__"]
            del t_node["_id"]
            _finaldata.update(t_node)
            
            # get additional files JSON
            for item in _datafiles:
                _node = sdk.cmd_getnode_bypath(path=item, db=db, fields=[])
                if not _node:
                    return common.INT_CommandError("Additional data file {} not found".format(item))
                del _node["__header__"]
                del _node["_id"]
                _finaldata.update(_node)
            
            # render email content template
            _render = _template.render(**_finaldata)
            
            # call email service
            _service_req_id = sdk.cmd_sendmail(content=_render, **_smtp)
            return common.SuccessResponse({"requestid":_service_req_id}, command=_parsed.command)
        except TemplateNotFound, e:
            return common.INT_CommandError("Template not found")
        except TemplateError, e:
            return common.INT_CommandError(e.message)
        
    def cmd_emailsend_status(self, commandline, sessionid, attachmentpath):
        """
        **{command}**

        **{command}** checks email processing status

        **SYNOPSIS**::

            {command} <request_id>

        **DESCRIPTION**:

        The **{command}** gets the status of a 'Send email' request
        
        **Arguments**::

            request_id    Processing Request Id returned from the 'Send email' command

        **Options**:

        *None*

        **Examples**:

        *None*
        """
        r = sdk.cmd_parsecommandline(command=commandline)
        _parsed = self.psr_emailstatus.parse_args(r["command"])
        request_id = _parsed.request_id
        
        _status = sdk.cmd_emailstatus(ticket=request_id)
        return common.SuccessResponse(_status, command=_parsed.command)        

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--id",action="store",type=int,default=1)
    parsed = parser.parse_args()

    s = Server(id=parsed.id)
    try:
        s.run()
    except KeyboardInterrupt:
        print "\nexiting"
