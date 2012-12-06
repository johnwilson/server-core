import json
import os
import re
import hashlib
import os
from pymongo import Connection
import redis
from uuid import uuid4
import sys
import time
import shutil
import math

from common import Service, Node, File, Directory
import common

class BFSService(Service):

    def __init__(self, id, name="bfs", configfile=None):
        Service.__init__(self, id, name, configfile)
        self.reserved_dbs = self.configreader["services"][self.name]["reserved_dbs"]
        self.collection = self.configreader["services"][self.name]["content_collection"]
        self.counter_collection = self.configreader["services"][self.name]["counter_collection"]

    def processRequest(self, command, command_data):
        _request = json.loads(command_data)
        if command == "subnode.get.all":
            return self.cmd_childnodes(**_request)
        elif command == "subnode.add":
            return self.cmd_addchild(**_request)
        elif command == "subnode.del":
            return self.cmd_removechild(**_request)
        elif command == "node.del":
            return self.cmd_removenode(**_request)
        elif command == "node.get":
            return self.cmd_getnode(**_request)
        elif command == "node.get.all":
            return self.cmd_getnodelist(**_request)
        elif command == "node.save":
            return self.cmd_savenode(**_request)
        elif command == "binary.save":
            return self.cmd_saveattachment(**_request)
        elif command == "binary.del":
            return self.cmd_removeattachment(**_request)
        elif command == "node.update.all":
            return self.cmd_updatenodes(**_request)
        elif command == "node.get.bypath":
            return self.cmd_getnode_bypath(**_request)
        elif command == "node.copy":
            return self.cmd_copynode(**_request)
        elif command == "db.make":
            return self.cmd_makedatabase(**_request)
        elif command == "db.del":
            return self.cmd_removedatabase(**_request)
        elif command == "db.copy":
            return self.cmd_copydatabase(**_request)
        elif command == "db.get.all":
            return self.cmd_listdatabases(**_request)
        elif command == "server.init":
            return self.cmd_rebuildserver(**_request)
        elif command == "authenticate":
            return self.authenticate(**_request)
        elif command == "user.new":
            return self.newuser(**_request)
        elif command == "user.del":
            return self.removeuser(**_request)
        elif command == "user.del.all":
            return self.removeuser_all(**_request)
        elif command == "user.show":
            return self.getuserinfo(**_request)
        elif command == "user.show.all":
            return self.getallusers(**_request)
        elif command == "user.passwd":
            return self.updatepassword(**_request)
        elif command == "user.dbaccess.grant":
            return self.grantdbaccess(**_request)
        elif command == "user.all.dbaccess.grant":
            return self.grantdbaccess_all(**_request)
        elif command == "user.dbaccess.revoke":
            return self.revokedbaccess(**_request)
        elif command == "user.all.dbaccess.revoke":
            return self.revokedbaccess_all(**_request)
        elif command == "user.dbaccess":
            return self.has_dbaccess(**_request)
        elif command == "user.activate":
            return self.activateuser(**_request)
        elif command == "user.deactivate":
            return self.deactivitateuser(**_request)
        elif command == "session.new":
            return self.cmd_createsession(**_request)
        elif command == "session.get":
            return self.cmd_getsession(**_request)
        elif command == "session.update":
            return self.cmd_updatesession(**_request)
        elif command == "session.drop":
            return self.cmd_dropsession(**_request)
        elif command == "memory.add":
            return self.cmd_additem(**_request)
        elif command == "memory.get":
            return self.cmd_getitem(**_request)
        elif command == "memory.getrange":
            return self.cmd_getrange(**_request)
        elif command == "memory.delete":
            return self.cmd_delete(**_request)
        elif command == "counter.update":
            return self.counter_update(**_request)
        elif command == "counter.list":
            return self.counter_list(**_request)
        elif command == "counter.clear":
            return self.counter_clear(**_request)
        elif command == "counter.get":
            return self.counter_get(**_request)
        elif command == "find":
            return self.cmd_find(**_request)
        else:
            return common.requestMethodNotFound("command '%s' doesn't exist" % command)

#===============================================================================
#   Bytengine file system functions
#===============================================================================

    def cmd_childnodes(self, **kwargs):
        docId = kwargs["docId"]
        db = kwargs["db"]        
        collection = self.collection
        fields = kwargs["fields"]
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        if len(fields) > 0:
            cursor = c[db][collection].find({"__header__.parent":docId},fields)
        else:
            cursor = c[db][collection].find({"__header__.parent":docId})
        _list = list(cursor)
        cursor.close()
        c.close()
        return common.SuccessResponse(_list)

    def cmd_addchild(self, **kwargs):
        parent_docId = kwargs["parent_docId"]
        child_docId = kwargs["child_docId"]
        db = kwargs["db"]
        collection = self.collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        tmp = {}
        parent_doc = c[db][collection].find_one({"_id":parent_docId},[])
        child_doc = c[db][collection].find_one({"_id":child_docId},["__header__"])
        if parent_doc and child_doc:
            c[db][collection].update({"_id":child_doc["_id"]},
                                     {"$set":{"__header__.parent":parent_doc["_id"]}},
                                     safe=True)
            # update path cache
            self.__pathcache_delpath(db,child_doc["_id"])

            return common.SuccessResponse(True)
        else:
            return common.INT_ServiceError("parent/child node doesn't exist")

    def cmd_removechild(self, **kwargs):
        docId = kwargs["docId"]
        db = kwargs["db"]
        collection = self.collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        tmp = {}
        doc = c[db][collection].find_one({"_id":docId},["__header__"])
        if doc:
            c[db][collection].update({"_id":child_doc["_id"]},
                                     {"$unset":{"__header__.parent":parent_doc["_id"]}},
                                     safe=True)
            return common.SuccessResponse(True)
        else:
            return common.INT_ServiceError("Document doesn't exist")

    def cmd_removenode(self, **kwargs):
        docId = kwargs["docId"]
        db = kwargs["db"]
        collection = self.collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        tmp = {}
        doc = c[db][collection].find_one({"_id":docId},["_id"])
        if not doc:
            return common.INT_ServiceError("Document doesn't exist")

        # cascade delete
        self.__recursive_delete__(doc["_id"],c[db][collection])
        return common.SuccessResponse(True)

    def __recursive_delete__(self, docId, collection):
        tmp = list(collection.find({"__header__.parent":docId},["_id"]))
        if len(tmp) > 0:
            for item in tmp:
                self.__recursive_delete__(item["_id"],collection)
        doc = collection.find_one({"_id":docId},["__header__"])
        collection.remove({"_id":docId})

        # remove from pathcache
        db = collection.database
        self.__pathcache_delpath(db,docId)

        # remove attachment if any
        if "filepointer" in doc["__header__"]:
            f = doc["__header__"]["filepointer"]
            if os.path.exists(f):
                os.remove(f)

    def cmd_getnode(self, **kwargs):
        query = kwargs["query"]
        db = kwargs["db"]
        collection = self.collection
        fields = kwargs["fields"]
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        if len(fields) > 0:
            doc = c[db][collection].find_one(query,fields)
        else:
            doc = c[db][collection].find_one(query)
        if not doc:
            return common.SuccessResponse(False)
        return common.SuccessResponse(doc)

    def cmd_getnodelist(self, **kwargs):
        query = kwargs["query"]
        db = kwargs["db"]
        collection = self.collection
        fields = kwargs["fields"]
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        if len(fields) > 0:
            cursor = c[db][collection].find(query,fields)
        else:
            cursor = c[db][collection].find_one(query)
        _list = list(cursor)
        cursor.close()
        c.close()
        return common.SuccessResponse(_list)

    def cmd_savenode(self, **kwargs):
        data = kwargs["data"]
        db = kwargs["db"]
        collection = self.collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        if not "_id" in data:
            _id = "%s:%s" % (uuid4().hex, time.time())
            data["_id"] = _id
        else:
            _id = data["_id"]
        c[db][collection].save(data,safe=True)
        return common.SuccessResponse(_id)

    def cmd_saveattachment(self, **kwargs):
        path = kwargs["path"]
        db = kwargs["db"]
        collection = self.collection

        if not os.path.exists(path):
            common.INT_ServiceError("Attachment doesn't exist")

        c = self.mongodbConnect()
        if not db in c.database_names():
            common.INT_ServiceError("Database doesn't exist")
        db_dir = os.path.join(self.configreader["services"][self.name]["attachments_dir"],db)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        filename = os.path.join(db_dir,uuid4().hex)
        shutil.copyfile(path,filename)
        return common.SuccessResponse(filename)

    def cmd_removeattachment(self, **kwargs):
        path = kwargs["path"]

        if not os.path.exists(path):
            common.INT_ServiceError("Attachment doesn't exist")
        os.unlink(path)
        return common.SuccessResponse(path)

    def cmd_updatenodes(self, **kwargs):
        query = kwargs["query"]
        updates = kwargs["updates"]
        db = kwargs["db"]
        collection = self.collection

        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        tmp = {}
        c[db][collection].update(query,updates,safe=True, multi=True)

        # update path cache if nodes name change
        if "$set" in updates and "__header__.name" in updates["$set"]:
            #get all updated nodes
            _node_id_list = []
            for item in c[db][collection].find(query,["_id"]):
                _node_id_list.append(item["_id"])
            #delete values from path cache
            for _id in _node_id_list:
                self.__pathcache_delpath(db,_id)
        return common.SuccessResponse(True)

    def cmd_getnode_bypath(self, **kwargs):
        path = kwargs["path"]
        fields = kwargs["fields"]
        db = kwargs["db"]        
        collection = self.collection

        # check if path in db 'pathcache' collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        _id = self.__pathcache_findbypath(db, path)
        if _id:
            cmd = {"query":{"_id":_id},
                   "db":db,
                   "collection":collection,
                   "fields":fields}
            result = self.cmd_getnode(**cmd)            
            if not result["data"]:
                # delete obsolete path from pathcache
                self.__pathcache_delpath(db,_id)
            else:
                return result
        # walk path in mongodb
        node = self.__walkpath__(path,c[db][collection],fields)        
        if node:
            # store path in pathcache
            self.__pathcache_addpath(db, path, node["_id"])
            return common.SuccessResponse(node)
        return common.SuccessResponse(False)
        
    def __pathcache_findbypath(self, db, path):
        path = os.path.normpath(path)
        pathlookup = "{database}:{path}".format(database=db, path=path)
        r_server = self.redisConnectPathCache()
        return r_server.get(pathlookup)
    
    def __pathcache_findbyid(self, db, id):
        idlookup = "{database}:{id}".format(database=db, id=id)
        r_server = self.redisConnectPathCache()
        return r_server.get(idlookup)
    
    def __pathcache_addpath(self, db, path, id):
        path = os.path.normpath(path)
        pathlookup = "{database}:{path}".format(database=db, path=path)        
        idlookup = "{database}:{id}".format(database=db, id=id)        
        r_server = self.redisConnectPathCache()
        r_server.set(pathlookup, id)
        r_server.set(idlookup, path)
    
    def __pathcache_delpath(self, db, id):
        idlookup = "{database}:{id}".format(database=db, id=id)
        r_server = self.redisConnectPathCache()
        path = r_server.get(idlookup)
        if path:
            pathlookup = "{database}:{path}".format(database=db, path=path)
            r_server.delete(idlookup)
            r_server.delete(pathlookup)

    def __pathtoarray__(self, path):
            path = os.path.normpath(path)
            result = re.findall(r"[a-zA-Z0-9._]+",path)
            if len(result) < 1:
                return ["/"]
            else:
                return result

    def __walkpath__(self, path, collection, returnfields):
            _path = self.__pathtoarray__(path)
            if len(returnfields) < 1:
                returnfields = None
            root_doc = collection.find_one({"__header__.name":"/"},returnfields)
            if len(_path) == 1:
                if _path[0] == "/":
                    return root_doc
            curr_doc = root_doc
            while len(_path) > 0:
                _name = _path.pop(0)
                curr_doc = collection.find_one({"__header__.parent":curr_doc["_id"], "__header__.name":_name},["__header__"])
                if curr_doc:
                    continue
                else:
                    return None

            #if path search incomplete raise exception
            if len(_path) > 0:
                return None
            else:
                #get full document info
                return collection.find_one(curr_doc["_id"],returnfields)

    def cmd_copynode(self, **kwargs):
        docId = kwargs["docId"]
        parentId = kwargs["parentId"]
        db = kwargs["db"]
        collection = self.collection

        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")
        tmp = {}
        doc = c[db][collection].find_one({"_id":docId},["_id"])
        parent = c[db][collection].find_one({"_id":parentId},["_id"])
        if not doc:
            return common.INT_ServiceError("Node doesn't exist")
        if not parent:
            return common.INT_ServiceError("Parent node doesn't exist")

        # cascade copy
        new_items_list = []
        self.__recursive_copy__(doc["_id"],parent["_id"],c[db][collection],new_items_list)
        return common.SuccessResponse(new_items_list[0])

    def __recursive_copy__(self, docId, parentId, collection, new_items_list):
        # get node to copy
        doc = collection.find_one({"_id":docId})

        # change doc id so mongodb ceates a new entry
        _id = "%s:%s" % (uuid4().hex, time.time())
        doc["_id"] = _id

        # copy attachment if any
        if "filepointer" in doc["__header__"]:
            f = doc["__header__"]["filepointer"]
            if os.path.exists(f):
                filename = os.path.join(os.path.dirname(f),uuid4().hex)
                shutil.copyfile(f,filename)
                doc["__header__"]["filepointer"] = filename
        doc["__header__"]["parent"] = parentId
        collection.save(doc)

        # add new id to list
        new_items_list.append(_id)

        #check if copied node item has subnodes
        tmp = list(collection.find({"__header__.parent":docId},["_id"]))
        if len(tmp) > 0:
            for item in tmp:
                self.__recursive_copy__(item["_id"],_id,collection,new_items_list)

    def cmd_makedatabase(self, **kwargs):
        db = kwargs["db"]
        if db in self.reserved_dbs:
            return common.INT_ServiceError("Invalid database name")
        c = self.mongodbConnect()
        if db in c.database_names():
            return common.INT_ServiceError("Database already exists")
        # create collections
        root = Directory()
        root.name="/"
        root.id = "%s:%s" % (uuid4().hex, time.time())
        c[db][self.collection].insert(root.serialize(),safe=True)

        # make attachments directory
        db_dir = os.path.join(self.configreader["services"][self.name]["attachments_dir"],db)
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)
        os.makedirs(db_dir)
        return common.SuccessResponse(True)

    def cmd_removedatabase(self, **kwargs):
        db = kwargs["db"]
        if db in self.reserved_dbs:
            return common.INT_ServiceError("Invalid database name")
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("Database doesn't exist")
        if db in self.reserved_dbs:
            return common.INT_ServiceError("Database cannot be deleted")
        
        # drop mongo db
        c.drop_database(db)
        
        # drop path cache keys from redis
        r_server = self.redisConnectPathCache()
        entries = r_server.keys(pattern='{0}:*'.format(db))
        if len(entries) > 0:
            r_server.delete(*entries)

        # delete attachments directory
        db_dir = os.path.join(self.configreader["services"][self.name]["attachments_dir"],db)
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)
        return common.SuccessResponse(True)

    def cmd_copydatabase(self, **kwargs):
        db_old = kwargs["db_old"]
        db_new = kwargs["db_new"]
        if db_old in self.reserved_dbs or db_new in self.reserved_dbs:
            return common.INT_ServiceError("Invalid database name")
        c = self.mongodbConnect()
        if db_new in c.database_names():
            return common.INT_ServiceError("Database already exists")
        if not db_old in c.database_names():
            return common.INT_ServiceError("Database doesn't exist")
        if db_old in self.reserved_dbs:
            return common.INT_ServiceError("Database cannot be copied")

        c.copy_database(db_old,db_new)
        # make attachments directory
        db_path_old = os.path.join(self.configreader["services"][self.name]["attachments_dir"], db_old)
        db_path_new = os.path.join(self.configreader["services"][self.name]["attachments_dir"], db_new)
        if os.path.exists(db_path_new):
            shutil.rmtree(db_path_new)
        if os.path.exists(db_path_old):
            shutil.copytree(db_path_old,db_path_new)

            return common.SuccessResponse(True)

    def cmd_rebuildserver(self, **kwargs):
        c = self.mongodbConnect()
        for db in c.database_names():
            if not db in self.reserved_dbs:
                c.drop_database(db)
                db_dir = os.path.join(self.configreader["services"][self.name]["attachments_dir"],db)
                if os.path.exists(db_dir):
                    shutil.rmtree(db_dir)
        r = self.redisConnect()
        r.flushall()
        return common.SuccessResponse(True)

    def cmd_listdatabases(self, **kwargs):
        c = self.mongodbConnect()
        tmp = []
        for db in c.database_names():
            if db not in self.reserved_dbs:
                tmp.append(db)
        return common.SuccessResponse(tmp)

    def cmd_find(self, **kwargs):
        queryparts = kwargs["queryparts"]
        db = kwargs["db"]
        collection = self.collection

        # check search directories
        dirnodelist = []
        dirpathLookup = {}
        for path in queryparts["from"]:
            _reply = self.cmd_getnode_bypath(path=path,
                                             db=db,
                                             collection=self.collection,
                                             fields=["_id"])
            _reply_dict = _reply
            if not _reply_dict["status"] == "ok":
                return common.INT_ServiceError("directory '%s' in 'From' not found" % path)
            if not _reply_dict["data"]:
                return common.INT_ServiceError("directory '%s' in 'From' not found" % path)
            _node = _reply_dict["data"]

            dirnodelist.append(_node["_id"])
            dirpathLookup[_node["_id"]] = path

        # buildup query
        query = {}
        query.update(queryparts["where"])
        if len(queryparts["and"]) > 0:
            query["$and"] = queryparts["and"]
        if len(queryparts["or"]) > 0:
            query["$or"] = queryparts["or"]

        query["__header__.type"] = "File"
        query["__header__.parent"] = {"$in":dirnodelist}

        returnfields = queryparts["select"]
        returnfields.append("__header__")

        c = self.mongodbConnect()
        cursor = c[db][collection].find(query,fields=returnfields)

        queryresult = []

        if cursor.count() > 0:
            # cursor management
            if "limit" in queryparts:
                cursor.limit(queryparts["limit"])

            if len(queryparts["sort"]) > 0:
                cursor.sort(queryparts["sort"])

            for item in cursor:
                _parentdir = dirpathLookup[item["__header__"]["parent"]]
                _filename = item["__header__"]["name"]
                if _parentdir == "/":
                    _filepath = "/%s" % _filename
                else:
                    _filepath = "%s/%s" % (_parentdir,_filename)
                row = {"path":_filepath}
                #remove sensitive data
                del item["_id"]
                del item["__header__"]
                row["content"] = item
                queryresult.append(row)
        cursor.close()

        return common.SuccessResponse(queryresult)

#===============================================================================
#   Counter functions
#===============================================================================

    def counter_get(self, **kwargs):
        countername = kwargs["counter"].strip()
        db = kwargs["db"]
        collection = self.counter_collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")

        # find existing counter if any
        _counter = c[db][collection].find_one({"name":countername},fields=["_id","value"])

        if not _counter:
            return common.INT_ServiceError("Counter %s not found" % countername)
        else:
            return common.SuccessResponse(int(_counter["value"]))

    def counter_update(self, **kwargs):
        countername = kwargs["counter"].strip()
        db = kwargs["db"]
        action = kwargs["action"]
        value = kwargs["value"]
        collection = self.counter_collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")

        # find existing counter if any
        _counter = c[db][collection].find_one({"name":countername},fields=["_id","value"])

        if not _counter:
            if action == "incr":
                _finalval = int(math.fabs(value))
            elif action == "decr":
                _finalval = int(math.fabs(value) * -1)
            elif action == "init":
                _finalval = int(value)
            else:
                return common.INT_ServiceError("Counter %s couldn't be updated" % countername)

            _counter = {"name":countername, "value":_finalval}
            _result = c[db][collection].insert(_counter,safe=True)
            if not _result:
                return common.INT_ServiceError("Counter %s couldn't be created" % countername)
        else:
            if action == "incr":
                _step = int(math.fabs(value))
                _finalval = _counter["value"] + _step
                _update_query = {"$inc":{"value":math.fabs(_step)}}
            elif action == "decr":
                _step = int(math.fabs(value) * -1)
                _finalval = _counter["value"] + _step
                _update_query = {"$inc":{"value":_step}}
            elif action == "init":
                _finalval = int(value)
                _update_query = {"$set":{"value":_finalval}}
            else:
                return common.INT_ServiceError("Counter %s couldn't be updated" % countername)
            c[db][collection].update({"_id":_counter["_id"]},_update_query,safe=True)

        return common.SuccessResponse(int(_finalval))

    def counter_list(self, **kwargs):
        db = kwargs["db"]
        collection = self.counter_collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")

        # find existing counter if any
        _result = []
        for _counter in c[db][collection].find():
            _result.append({"name":_counter["name"], "currentcount":int(_counter["value"])})
        return common.SuccessResponse(_result)

    def counter_clear(self, **kwargs):
        countername = kwargs["counter"].strip()
        db = kwargs["db"]
        collection = self.counter_collection
        c = self.mongodbConnect()
        if not db in c.database_names():
            return common.INT_ServiceError("database not found")

        # find existing counter if any
        _counter = c[db][collection].find_one({"name":countername},fields=["_id"])

        if not _counter:
            return common.INT_ServiceError("Counter %s not found" % countername)
        else:
            c[db][collection].remove({"_id":_counter["_id"]},safe=True)
            return common.SuccessResponse(True)

#===============================================================================
#   Security functions
#===============================================================================

    def authenticate(self, **kwargs):
        username = kwargs["username"]
        password = kwargs["password"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username},
                                   ["username","active","salt","password"])
        c.close()
        if not doc:
            return common.INT_ServiceError("user doesn't exist")
        if not doc["active"]:
            return common.INT_ServiceError("authentication failed")

        encrpt_pass = hashlib.sha1(doc["salt"] + password).hexdigest()
        if encrpt_pass == doc["password"]:
            return common.SuccessResponse("user authenticated")
        else:
            return common.INT_ServiceError("authentication failed")

    def newuser(self, **kwargs):
        username = self.validate_username(kwargs["username"])
        if not username:
            return common.INT_ServiceError("invalid username")
        password = self.validate_password(kwargs["password"])
        if not password:
            return common.INT_ServiceError("invalid password")
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username},["_id"])
        if doc:
            c.close()
            return common.INT_ServiceError("username already exists")

        salt = os.urandom(16).encode("hex")
        encrypt_password = hashlib.sha1(salt + password).hexdigest()
        doc = {"username":username,"password":encrypt_password,"salt":salt,
               "databases":[],"quotas":{},"active":True}
        _id = c[db][coll].save(doc,safe=True)
        c.close()
        return common.SuccessResponse(unicode(_id))

    def removeuser(self, **kwargs):
        username = kwargs["username"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username})
        if not doc:
            c.close()
            return common.INT_ServiceError("user doesn't exist")
        c[db][coll].remove(doc["_id"])
        c.close()
        return common.SuccessResponse(True)

    def removeuser_all(self, **kwargs):
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        c[db][coll].remove()
        c.close()
        return common.SuccessResponse(True)

    def getuserinfo(self, **kwargs):
        username = kwargs["username"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username})
        c.close()
        if not doc:
            return common.INT_ServiceError("user doesn't exist")
        del doc["_id"]
        return common.SuccessResponse(doc)

    def getallusers(self, **kwargs):
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]

        cursor = c[db][coll].find()
        _list = []
        for item in cursor:
            _list.append(item["username"])
        reply = {"count":len(_list),"users":_list}
        cursor.close()
        c.close()
        return common.SuccessResponse(reply)

    def updatepassword(self, **kwargs):
        username = kwargs["username"]
        if " " in kwargs["password"]:
            return common.INT_ServiceError("password cannot contain spaces")
        password = self.validate_password(kwargs["password"])
        if not password:
            return common.INT_ServiceError("invalid password")
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username})
        if not doc:
            c.close()
            return common.INT_ServiceError("user doesn't exist")

        salt = os.urandom(16).encode("hex")
        encrypt_password = hashlib.sha1(salt + password).hexdigest()
        doc["password"] = encrypt_password
        doc["salt"] = salt
        _id = c[db][coll].save(doc,safe=True)
        c.close()
        return common.SuccessResponse(unicode(_id))

    def grantdbaccess(self, **kwargs):
        username = kwargs["username"]
        database = kwargs["database"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username},["_id"])
        if not doc:
            c.close()
            return common.INT_ServiceError("user doesn't exist")
        c[db][coll].update({"_id":doc["_id"]}, {"$addToSet":{"databases":database}})
        c.close()
        return common.SuccessResponse(True)

    def grantdbaccess_all(self, **kwargs):
        database = kwargs["database"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        c[db][coll].update({"databases":{"$exists":1}}, {"$addToSet":{"databases":database}}, multi=True)
        c.close()
        return common.SuccessResponse(True)

    def revokedbaccess(self, **kwargs):
        username = kwargs["username"]
        database = kwargs["database"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username},["_id"])
        if not doc:
            c.close()
            return common.INT_ServiceError("user doesn't exist")
        c[db][coll].update({"_id":doc["_id"]}, {"$pull":{"databases":database}})
        c.close()
        return common.SuccessResponse(True)

    def revokedbaccess_all(self, **kwargs):
        database = kwargs["database"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        c[db][coll].update({"databases":{"$exists":1}}, {"$pull":{"databases":database}}, multi=True)
        c.close()
        return common.SuccessResponse(True)

    def has_dbaccess(self, **kwargs):
        username = kwargs["username"]
        database = kwargs["database"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username,"databases":database},["_id"])
        c.close()
        if doc:
            return common.SuccessResponse(True)
        else:
            return common.SuccessResponse(False)

    def activateuser(self, **kwargs):
        username = kwargs["username"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username},["_id"])
        if not doc:
            c.close()
            return common.INT_ServiceError("user doesn't exist")

        c[db][coll].update({"_id":doc["_id"]},{"$set":{"active":True}},safe=True)
        c.close()
        return common.SuccessResponse(True)

    def deactivitateuser(self, **kwargs):
        username = kwargs["username"]
        c = self.mongodbConnect()
        db = self.configreader["mongodb"]["sysdatabase"]
        coll = self.configreader["services"][self.name]["security_collection"]
        doc = c[db][coll].find_one({"username":username},["_id"])
        if not doc:
            c.close()
            return common.INT_ServiceError("user doesn't exist")

        c[db][coll].update({"_id":doc["_id"]},{"$set":{"active":False}},safe=True)
        c.close()
        return common.SuccessResponse(True)

#===============================================================================
#   Application Cache functions
#===============================================================================

    def cmd_additem(self, **kwargs):
        if "pointer" in kwargs:
            pointer = kwargs["pointer"]
            isnew = False
        else:
            pointer = hashlib.sha224(uuid4().hex).hexdigest()
            isnew = True
        r_server = self.redisConnectCache()
        reply = r_server.rpush(pointer,kwargs["data"])
        if isnew:
            r_server.expire(pointer,self.configreader["services"][self.name]["cache_timeout"])
        if not reply:
            return common.INT_ServiceError("data not saved")
        return common.SuccessResponse(pointer)

    def cmd_getitem(self, **kwargs):
        r_server = self.redisConnectCache()
        data = r_server.lindex(kwargs["pointer"], kwargs["index"])
        if not data:
            return common.INT_ServiceError("data not found")
        return common.SuccessResponse(data)

    def cmd_getrange(self, **kwargs):
        r_server = self.redisConnectCache()
        data = r_server.lrange(kwargs["pointer"], kwargs["start"], kwargs["end"])
        if not data:
            return common.INT_ServiceError("data not found")
        return common.SuccessResponse(data)

    def cmd_delete(self, **kwargs):
        r_server = self.redisConnectCache()
        pointer = kwargs.pop("pointer")
        reply = r_server.delete(pointer)
        if not reply:
            return common.INT_ServiceError("pointer not found")
        return common.SuccessResponse(True)

#===============================================================================
#   Session functions
#===============================================================================

    def cmd_createsession(self, **kwargs):
        username=kwargs["username"]
        isroot=kwargs["isroot"]
        mode = kwargs["mode"]
        database = kwargs["database"]
        r_server = self.redisConnectSession()
        
        if mode == "usermode":
            # check if session available
            _pattern = "*:{0}:UM".format(username)
            _key_list = r_server.keys(pattern=_pattern)
            _max = self.configreader["services"][self.name]["session_max_count"]
            if not len(_key_list) < _max:
                return common.INT_SessionError("maximum number of usermode sessions reached")
            _timeout = self.configreader["services"][self.name]["session_timeout_long"]
            ticket = hashlib.sha224(uuid4().hex).hexdigest()
            _key = "{0}:{1}:UM".format(ticket,username)
            r_server.hset(_key,"database",database)
            r_server.hset(_key,"isroot",isroot)
            r_server.hset(_key,"username",username)
            r_server.hset(_key,"mode","usermode")
            r_server.expire(_key,_timeout)
        else: # application mode
            if not database or len(database) < 1:
                return common.INT_SessionError("invalid session database")
            _timeout = self.configreader["services"][self.name]["session_timeout"]
            # check if session available
            _pattern = "*:{0}:{1}:AM".format(username,database)
            _key_list = r_server.keys(pattern=_pattern)
            if len(_key_list) > 0:
                _key = _key_list[0]
                # reset timeout
                r_server.expire(_key,_timeout)
                ticket = _key.split(":")[0]                
            else:
                ticket = hashlib.sha224(uuid4().hex).hexdigest()
                _key = "{0}:{1}:{2}:AM".format(ticket,username,database)
                r_server.hset(_key,"database",database)
                r_server.hset(_key,"isroot",isroot)
                r_server.hset(_key,"username",username)
                r_server.hset(_key,"mode","appmode")
                r_server.expire(_key,_timeout)
        return common.SuccessResponse(ticket)
    
    def cmd_dropsession(self, **kwargs):
        # used to logout of usermode sessions
        username=kwargs["username"]
        ticket = kwargs["ticket"]
        
        # find session and delete
        r_server = self.redisConnectSession()
        _key = "{0}:{1}:UM".format(ticket,username)
        if r_server.exists(_key):
            r_server.delete(_key)
            return common.SuccessResponse(True)
        
        # else delete random session        
        _pattern = "*:{0}:UM".format(username)
        _key_list = r_server.keys(pattern=_pattern)
        if len(_key_list) > 0:
            _key = _key_list[0]
            r_server.delete(_key)
            return common.SuccessResponse(True)
        else:
            return common.SuccessResponse(False)

    def cmd_getsession(self, **kwargs):
        r_server = self.redisConnectSession()
        ticket = kwargs["ticket"]
        # get first matching key
        _match = r_server.keys(pattern="{0}:*".format(ticket))
        if len(_match) < 1:
            return common.INT_SessionError("Session has expired")
        _key = _match[0]
        data = r_server.hgetall(_key)
        if len(data) > 0:
            if "isroot" in data:
                _isroot = data["isroot"].lower()
                if _isroot == "true" or _isroot == "1" or _isroot == "yes":
                    data["isroot"] = True
                else:
                    data["isroot"] = False
            # reset timeout
            if _key.endswith(":AM"):
                _timeout = self.configreader["services"][self.name]["session_timeout"]
                r_server.expire(_key,_timeout)
            return common.SuccessResponse(data)
        r_server.delete(_key)
        return common.INT_SessionError("Invalid Session Data")

    def cmd_updatesession(self, **kwargs):
        r_server = self.redisConnectSession()
        ticket = kwargs.pop("ticket")
        # get first matching key
        _match = r_server.keys(pattern="{0}:*".format(ticket))
        if len(_match) < 1:
            return common.INT_SessionError("Session has expired")
        _key = _match[0]
        if not r_server.exists(_key):
            return common.INT_SessionError("Session has expired")
        for key in kwargs:
            r_server.hset(_key, key, kwargs[key])
        # reset timeout
        if _key.endswith(":AM"):
            _timeout = self.configreader["services"][self.name]["session_timeout"]
            r_server.expire(_key,_timeout)
        return common.SuccessResponse(True)

#===============================================================================
#   Helper functions
#===============================================================================

    def mongodbConnect(self):
        return Connection(host=self.configreader["mongodb"]["host"],
                          port=self.configreader["mongodb"]["port"])

    def redisConnectCache(self):
        return redis.Redis(host=self.configreader["redis"]["host"],
                           port=self.configreader["redis"]["port"],
                           db=self.configreader["redis"]["cachedb"])

    def redisConnectSession(self):
        return redis.Redis(host=self.configreader["redis"]["host"],
                           port=self.configreader["redis"]["port"],
                           db=self.configreader["redis"]["sessiondb"])
    
    def redisConnectPathCache(self):
        return redis.Redis(host=self.configreader["redis"]["host"],
                           port=self.configreader["redis"]["port"],
                           db=self.configreader["redis"]["pathcachedb"])

    def validate_username(self, value):
        pattern = r"^[a-z]{1}([_]{0,1}[a-zA-Z0-9]{1,})+$"
        m = re.search(pattern,value)
        if not m:
            return None
        result = m.group()
        if result != value:
            return None
        return result

    def validate_password(self, value):
        pattern = r"^\w{8,}$"
        m = re.search(pattern,value)
        if not m:
            return None
        result = m.group()
        if result != value:
            return None
        return result

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--id",action="store",type=int,default=1)
    parsed = parser.parse_args()
    
    s = BFSService(id=parsed.id)
    try:
        s.run()
    except KeyboardInterrupt:
        print "\nexiting"
