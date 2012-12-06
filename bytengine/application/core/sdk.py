import zmq
import json
import logging
import os
import redis
import types

from common import Node, File, Directory, BytengineError
import common

#-------------------------------------------------------------------------------
#    Logging settings
#-------------------------------------------------------------------------------

Logger = logging.getLogger("bytengine.core")
formatter = logging.Formatter('%(asctime)-6s: %(name)s - %(levelname)s - %(message)s')
consoleLogger = logging.StreamHandler()
consoleLogger.setFormatter(formatter)
Logger.addHandler(consoleLogger)

#-------------------------------------------------------------------------------
#    Configuration settings manager
#-------------------------------------------------------------------------------

configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
CONFIG_PARSER = json.load(open(configfile,"r"))

#-------------------------------------------------------------------------------
#    Common classes and functions
#-------------------------------------------------------------------------------

# Service remote procedure call (rpc)
def service_rpc(service_name, request_type, command, params, timeout=10):
    query = u"%s : %s : %s : %s" % (service_name, request_type,
                                    command, params)
    _address = CONFIG_PARSER["bytengine"]["services"]["req_address"]
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.connect(_address)
    sock.send_string(query)

    # use poll for timeouts
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    if poller.poll(timeout * 1000):
        message_raw = sock.recv_string()
    else:
        raise IOError("Timeout processing service query")

    sock.close()
    ctx.term()
    
    # parse service json response
    try:
        message = json.loads(message_raw)
    except Exception, err:
        err_msg = common.ErrorResponse("service call failed, contact admin")
        raise BytengineError(err_msg)
    
    if not message["status"] == "ok":
        raise BytengineError(message)
    return message["data"]

# Command remote procedure call (rpc)
def command_rpc(command, session="", attachment="", namespace="core", timeout=10, return_raw=False):
    query = u"{session}:{attachment}:{namespace}:{command}".format(session=session,
                                                                   attachment=attachment,
                                                                   namespace=namespace,
                                                                   command=command)
    _address = CONFIG_PARSER["bytengine"]["commands"]["req_address"]
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.connect(_address)
    sock.send_string(query)

    # use poll for timeouts
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    if poller.poll(timeout * 1000):
        msg_raw = sock.recv_string()
    else:
        raise IOError("Timeout processing command query")
    sock.close()
    ctx.term()
    if return_raw:
        return msg_raw
    else:
        _result = json.loads(msg_raw)
        return _result

#-------------------------------------------------------------------------------
#    Session API
#-------------------------------------------------------------------------------

def cmd_createsession(**kargs):
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    assert "isroot" in kargs, "isroot parameter missing"
    assert type(kargs["isroot"]) == types.BooleanType, "isroot type must be 'Boolean'"
    
    assert "database" in kargs, "database parameter missing"
    assert type(kargs["database"]) in types.StringTypes, "database type must be 'String'"
    
    assert "mode" in kargs, "mode parameter missing"
    assert type(kargs["mode"]) in types.StringTypes, "mode type must be 'String'"
    
    req = json.dumps({"username":kargs["username"],
                      "isroot":kargs["isroot"],
                      "mode":kargs["mode"],
                      "database":kargs["database"]})
    msg = service_rpc("bfs","api","session.new",req)
    return msg

def cmd_dropsession(**kargs):
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    if "ticket" in kargs:
        req = json.dumps({"username":kargs["username"], "ticket":kargs["ticket"]})
    else:
        req = json.dumps({"username":kargs["username"], "ticket":""})
    msg = service_rpc("bfs","api","session.drop",req)
    return msg

def cmd_getsession(**kargs):
    assert "ticket" in kargs, "ticket parameter missing"
    assert type(kargs["ticket"]) in types.StringTypes, "ticket type must be 'String'"
    
    ticket = kargs["ticket"]
    msg = service_rpc("bfs","api","session.get",json.dumps({"ticket":ticket}))
    return msg

def cmd_updatesession(**kargs):
    assert "ticket" in kargs, "ticket parameter missing"
    assert type(kargs["ticket"]) in types.StringTypes, "ticket type must be 'String'"
    
    ticket = kargs["ticket"]
    msg = service_rpc("bfs","api","session.get",json.dumps({"ticket":ticket}))
    session_data = msg

    # update session
    session_data.update(kargs)
    msg = service_rpc("bfs","api","session.update",json.dumps(session_data))
    return msg

#-------------------------------------------------------------------------------
#    Parser API
#-------------------------------------------------------------------------------

def cmd_parsecommandline(**kargs):
    assert "command" in kargs, "command parameter missing"
    assert type(kargs["command"]) in types.StringTypes, "command type must be 'String'"
    
    msg = service_rpc("parser","api","parser.commandline",kargs["command"])
    return msg

def cmd_parsecommandline_json(**kargs):
    assert "command" in kargs, "command parameter missing"
    assert type(kargs["command"]) in types.StringTypes, "command type must be 'String'"
    
    msg = service_rpc("parser","api","parser.jsoncommandline",kargs["command"])
    return msg

def cmd_parsebql(**kargs):
    assert "query" in kargs, "query parameter missing"
    assert type(kargs["query"]) in types.StringTypes, "query type must be 'String'"
    
    msg = service_rpc("parser","api","parser.bql",kargs["query"])
    return msg

#-------------------------------------------------------------------------------
#    Counter API
#-------------------------------------------------------------------------------

def cmd_counter_incr(**kargs):
    assert "counter" in kargs, "counter parameter missing"
    assert type(kargs["counter"]) in types.StringTypes, "counter type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in  types.StringTypes, "db type must be 'String'"
    assert "value" in kargs, "value parameter missing"
    assert type(kargs["value"]) == types.IntType, "value type must be 'Int'"
    
    req = json.dumps({"db":kargs["db"],
                      "value":kargs["value"],
                      "counter":kargs["counter"],
                      "action":"incr"})
    msg = service_rpc("bfs","api","counter.update",req)
    return msg

def cmd_counter_decr(**kargs):
    assert "counter" in kargs, "counter parameter missing"
    assert type(kargs["counter"]) in types.StringTypes, "counter type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in  types.StringTypes, "db type must be 'String'"
    assert "value" in kargs, "value parameter missing"
    assert type(kargs["value"]) == types.IntType, "value type must be 'Int'"
    
    req = json.dumps({"db":kargs["db"],
                      "value":kargs["value"],
                      "counter":kargs["counter"],
                      "action":"decr"})
    msg = service_rpc("bfs","api","counter.update",req)
    return msg

def cmd_counter_init(**kargs):
    assert "counter" in kargs, "counter parameter missing"
    assert type(kargs["counter"]) in types.StringTypes, "counter type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in  types.StringTypes, "db type must be 'String'"
    assert "value" in kargs, "value parameter missing"
    assert type(kargs["value"]) == types.IntType, "value type must be 'Int'"
    
    req = json.dumps({"db":kargs["db"],
                      "value":kargs["value"],
                      "counter":kargs["counter"],
                      "action":"init"})
    msg = service_rpc("bfs","api","counter.update",req)
    return msg

def cmd_counter_get(**kargs):
    assert "counter" in kargs, "counter parameter missing"
    assert type(kargs["counter"]) in types.StringTypes, "counter type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in  types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"db":kargs["db"],
                      "counter":kargs["counter"]})
    msg = service_rpc("bfs","api","counter.get",req)
    return msg

def cmd_counter_list(**kargs):
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in  types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"db":kargs["db"]})
    msg = service_rpc("bfs","api","counter.list",req)
    return msg

def cmd_counter_clear(**kargs):
    assert "counter" in kargs, "counter parameter missing"
    assert type(kargs["counter"]) in types.StringTypes, "counter type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in  types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"db":kargs["db"],
                      "counter":kargs["counter"]})
    msg = service_rpc("bfs","api","counter.clear",req)
    return msg

#-------------------------------------------------------------------------------
#    Security API
#-------------------------------------------------------------------------------

def cmd_authenticate(**kargs):
    assert "password" in kargs, "password parameter missing"
    assert type(kargs["password"]) in types.StringTypes, "password type must be 'String'"
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"password":kargs["password"],
                      "username":kargs["username"]})
    msg = service_rpc("bfs","api","authenticate",req)
    return msg

def cmd_newuser(**kargs):
    assert "password" in kargs, "password parameter missing"
    assert type(kargs["password"]) in types.StringTypes, "password type must be 'String'"
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"password":kargs["password"],
                      "username":kargs["username"]})
    msg = service_rpc("bfs","api","user.new",req)
    return msg

def cmd_removeuser(**kargs):
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"username":kargs["username"]})
    msg = service_rpc("bfs","api","user.del",req)
    return msg

def cmd_removealluser(**kargs):
    msg = service_rpc("bfs","api","user.del.all","{}")
    return msg

def cmd_getuser(**kargs):
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"username":kargs["username"]})
    msg = service_rpc("bfs","api","user.show",req)
    return msg

def cmd_getalluser(**kargs):
    msg = service_rpc("bfs","api","user.show.all","{}")
    return msg

def cmd_updatepasswd(**kargs):
    assert "password" in kargs, "password parameter missing"
    assert type(kargs["password"]) in types.StringTypes, "password type must be 'String'"
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"password":kargs["password"],
                      "username":kargs["username"]})
    msg = service_rpc("bfs","api","user.passwd",req)
    return msg

def cmd_grantdbaccess(**kargs):
    assert "database" in kargs, "database parameter missing"
    assert type(kargs["database"]) in types.StringTypes, "database type must be 'String'"
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"database":kargs["database"],
                      "username":kargs["username"]})
    msg = service_rpc("bfs","api","user.dbaccess.grant",req)
    return msg

def cmd_grantalldbaccess(**kargs):
    assert "database" in kargs, "database parameter missing"
    assert type(kargs["database"]) in types.StringTypes, "database type must be 'String'"
    
    req = json.dumps({"database":kargs["database"]})
    msg = service_rpc("bfs","api","user.all.dbaccess.grant",req)
    return msg

def cmd_revokedbaccess(**kargs):
    assert "database" in kargs, "database parameter missing"
    assert type(kargs["database"]) in types.StringTypes, "database type must be 'String'"
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"database":kargs["database"],
                      "username":kargs["username"]})
    msg = service_rpc("bfs","api","user.dbaccess.revoke",req)
    return msg

def cmd_revokealldbaccess(**kargs):
    assert "database" in kargs, "database parameter missing"
    assert type(kargs["database"]) in types.StringTypes, "database type must be 'String'"
    
    req = json.dumps({"database":kargs["database"]})
    msg = service_rpc("bfs","api","user.all.dbaccess.revoke",req)
    return msg

def cmd_hasdbaccess(**kargs):
    assert "database" in kargs, "database parameter missing"
    assert type(kargs["database"]) in types.StringTypes, "database type must be 'String'"
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"database":kargs["database"],
                      "username":kargs["username"]})
    msg = service_rpc("bfs","api","user.dbaccess",req)
    return msg

def cmd_activateuser(**kargs):
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"username":kargs["username"]})
    msg = service_rpc("bfs","api","user.activate",req)
    return msg

def cmd_deactivateuser(**kargs):
    assert "username" in kargs, "username parameter missing"
    assert type(kargs["username"]) in types.StringTypes, "username type must be 'String'"
    
    req = json.dumps({"username":kargs["username"]})
    msg = service_rpc("bfs","api","user.deactivate",req)
    return msg

#-------------------------------------------------------------------------------
#    BFS API
#-------------------------------------------------------------------------------

def cmd_childnodes(**kargs):
    assert "docId" in kargs, "docId parameter missing"
    assert type(kargs["docId"]) in types.StringTypes, "docId type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    assert "fields" in kargs, "fields parameter missing"
    assert type(kargs["fields"]) is types.ListType, "fields type must be 'List'"
    
    req = json.dumps({"docId":kargs["docId"],
                      "db":kargs["db"],
                      "fields":kargs["fields"]})

    msg = service_rpc("bfs","api","subnode.get.all",req)
    return msg

def cmd_addchild(**kargs):
    assert "parent_docId" in kargs, "parent_docId parameter missing"
    assert type(kargs["parent_docId"]) in types.StringTypes, "parent_docId type must be 'String'"
    assert "child_docId" in kargs, "child_docId parameter missing"
    assert type(kargs["child_docId"]) in types.StringTypes, "child_docId type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"parent_docId":kargs["parent_docId"],
                      "child_docId":kargs["child_docId"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","subnode.add",req)
    return msg

def cmd_removechild(**kargs):
    assert "docId" in kargs, "docId parameter missing"
    assert type(kargs["docId"]) in types.StringTypes, "docId type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"docId":kargs["docId"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","subnode.del",req)
    return msg

def cmd_removenode(**kargs):
    assert "docId" in kargs, "docId parameter missing"
    assert type(kargs["docId"]) in types.StringTypes, "docId type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"docId":kargs["docId"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","node.del",req)
    return msg

def cmd_getnode(**kargs):
    assert "query" in kargs, "query parameter missing"
    assert type(kargs["query"]) is types.DictType, "query type must be 'Dictionary'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    assert "fields" in kargs, "fields parameter missing"
    assert type(kargs["fields"]) is types.ListType, "fields type must be 'List'"
    
    req = json.dumps({"query":kargs["query"],
                      "fields":kargs["fields"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","node.get",req)
    return msg

def cmd_getnodelist(**kargs):
    assert "query" in kargs, "query parameter missing"
    assert type(kargs["query"]) is types.DictType, "query type must be 'Dictionary'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    assert "fields" in kargs, "fields parameter missing"
    assert type(kargs["fields"]) is types.ListType, "fields type must be 'List'"
    
    req = json.dumps({"query":kargs["query"],
                      "fields":kargs["fields"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","node.get.all",req)
    return msg

def cmd_savenode(**kargs):
    assert "data" in kargs, "data parameter missing"
    assert type(kargs["data"]) is types.DictType, "data type must be 'Dictionary'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"data":kargs["data"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","node.save",req)
    return msg

def cmd_saveattachment(**kargs):
    assert "path" in kargs, "path parameter missing"
    assert type(kargs["path"]) in types.StringTypes, "path type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"path":kargs["path"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","binary.save",req)
    return msg

def cmd_removeattachment(**kargs):
    assert "path" in kargs, "path parameter missing"
    assert type(kargs["path"]) in types.StringTypes, "path type must be 'String'"
    
    req = json.dumps({"path":kargs["path"]})
    msg = service_rpc("bfs","api","binary.del",req)
    return msg

def cmd_updatenodes(**kargs):
    assert "query" in kargs, "query parameter missing"
    assert type(kargs["query"]) is types.DictType, "query type must be 'Dictionary'"
    assert "updates" in kargs, "updates parameter missing"
    assert type(kargs["updates"]) is types.DictType, "updates type must be 'Dictionary'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"query":kargs["query"],
                      "updates":kargs["updates"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","node.update.all",req)
    return msg

def cmd_getnode_bypath(**kargs):
    assert "path" in kargs, "path parameter missing"
    assert type(kargs["path"]) in types.StringTypes, "path type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    assert "fields" in kargs, "fields parameter missing"
    assert type(kargs["fields"]) is types.ListType, "fields type must be 'List'"
    
    req = json.dumps({"path":kargs["path"],
                      "fields":kargs["fields"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","node.get.bypath",req)
    return msg

def cmd_copynode(**kargs):
    assert "docId" in kargs, "docId parameter missing"
    assert type(kargs["docId"]) in types.StringTypes, "docId type must be 'String'"
    assert "parentId" in kargs, "parentId parameter missing"
    assert type(kargs["parentId"]) in types.StringTypes, "parentId type must be 'String'"
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    
    req = json.dumps({"docId":kargs["docId"],
                      "parentId":kargs["parentId"],
                      "db":kargs["db"]})
    msg = service_rpc("bfs","api","node.copy",req)
    return msg

def cmd_makedatabase(**kargs):
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"

    req = json.dumps({"db":kargs["db"]})
    msg = service_rpc("bfs","api","db.make",req)
    return msg

def cmd_removedatabase(**kargs):
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"

    req = json.dumps({"db":kargs["db"]})
    msg = service_rpc("bfs","api","db.del",req)
    return msg

def cmd_copydatabase(**kargs):
    assert "db_old" in kargs, "db_old parameter missing"
    assert type(kargs["db_old"]) in types.StringTypes, "db_old type must be 'String'"
    assert "db_new" in kargs, "db_new parameter missing"
    assert type(kargs["db_new"]) in types.StringTypes, "db_new type must be 'String'"
    
    req = json.dumps({"db_old":kargs["db_old"],
                      "db_new":kargs["db_new"]})
    msg = service_rpc("bfs","api","db.copy",req)
    return msg

def cmd_rebuildserver(**kargs):
    msg = service_rpc("bfs","api","server.init","{}")
    return msg

def cmd_listdatabases(**kargs):
    msg = service_rpc("bfs","api","db.get.all","{}")
    return msg

def cmd_find(**kargs):
    assert "db" in kargs, "db parameter missing"
    assert type(kargs["db"]) in types.StringTypes, "db type must be 'String'"
    assert "query" in kargs, "query parameter missing"
    assert type(kargs["query"]) in types.StringTypes, "query type must be 'String'"
    
    queryparts = cmd_parsebql(query=kargs["query"])

    req = json.dumps({"db":kargs["db"],"queryparts":queryparts})
    msg = service_rpc("bfs","api","find",req)
    return msg

#-------------------------------------------------------------------------------
#    Email API
#-------------------------------------------------------------------------------

def cmd_sendmail(**kargs):
    assert "subject" in kargs, "subject parameter missing"
    assert type(kargs["subject"]) in types.StringTypes, "subject type must be 'String'"
    assert "author" in kargs, "author parameter missing"
    assert type(kargs["author"]) in types.StringTypes, "author type must be 'String'"
    assert "to" in kargs, "to parameter missing"
    assert type(kargs["to"]) is types.ListType, "to type must be 'List'"
    assert "from" in kargs, "from parameter missing"
    assert type(kargs["from"]) in types.StringTypes, "from type must be 'String'"
    assert "content" in kargs, "content parameter missing"
    assert type(kargs["content"]) in types.StringTypes, "content type must be 'String'"
    assert "mailserver" in kargs, "mailserver parameter missing"
    assert type(kargs["mailserver"]) in types.StringTypes, "mailserver type must be 'String'"
    assert "password" in kargs, "password parameter missing"
    assert type(kargs["password"]) in types.StringTypes, "password type must be 'String'"
    
    req = json.dumps({"subject":kargs["subject"],
                      "to":kargs["to"],
                      "from":kargs["from"],
                      "content":kargs["content"],
                      "author":kargs["author"],
                      "mailserver":kargs["mailserver"],
                      "password":kargs["password"]})

    msg = service_rpc("email","api","email.send",req)
    return msg

def cmd_emailstatus(**kargs):
    assert "ticket" in kargs, "ticket parameter missing"
    assert type(kargs["ticket"]) in types.StringTypes, "ticket type must be 'String'"
    
    req = json.dumps({"ticket":kargs["ticket"]})
    msg = service_rpc("emailcheck","api","email.checkstatus",req)
    return msg
