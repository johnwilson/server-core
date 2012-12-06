import json
import unittest
import zmq
import os
import datetime
import copy
import sys

# add bytengine to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

from bytengine.application.core.common import Node

class TestParserService(unittest.TestCase):
    def setUp(self):
        configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        reader = json.load(open(configfile,"r"))

        self.endpoint = reader["bytengine"]["services"]["req_address"]
        self.context = zmq.Context()

    def test_1(self):
        """test command line parser"""
        socket = self.context.socket(zmq.REQ)
        socket.connect(self.endpoint)

        _data = u"parser : api : parser.commandline : makefile -p=/tmp/file1"
        socket.send_string(_data)
        msg = socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"parser : api : commandline : makefile -p=/tmp/file1"
        socket.send_string(_data)
        msg = socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'error')

    def test_2(self):
        """test bql parser"""
        socket = self.context.socket(zmq.REQ)
        socket.connect(self.endpoint)

        _data = u"parser : api : parser.bql : select('name') from ('/users')"
        socket.send_string(_data)
        msg = socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"parser : api : parser.bql : select('name') from '/users'"
        socket.send_string(_data)
        msg = socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'error')

    def tearDown(self):
        self.context.term()

class TestSecurityService(unittest.TestCase):
    def setUp(self):
        configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        reader = json.load(open(configfile,"r"))

        self.endpoint = reader["bytengine"]["services"]["req_address"]
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)

    def test_1(self):
        """test clear all users"""

        # short password error check
        _data = u'bfs : api: user.del.all :{}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

    def test_2(self):
        """test new user"""

        # short password error check
        _data = u'bfs : api: user.new : {"username":"testuser1","password":"admin"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'error')

        _data = u'bfs : api: user.new : {"username":"testuser1","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

    def test_3(self):
        """test authenticate user"""

        _data = u'bfs : api: authenticate : {"username":"testuser1","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        # change password
        _data = u'bfs : api: user.passwd : {"username":"testuser1","password":"910111213"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: authenticate : {"username":"testuser1","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'error')

        _data = u'bfs : api: authenticate : {"username":"testuser1","password":"910111213"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        # reset password to original
        _data = u'bfs : api: user.passwd : {"username":"testuser1","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: authenticate : {"username":"testuser1","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        # activate / deactivate test
        _data = u'bfs : api: user.deactivate : {"username":"testuser1"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: authenticate : {"username":"testuser1","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'error')

        _data = u'bfs : api: user.activate : {"username":"testuser1"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: authenticate : {"username":"testuser1","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

    def test_4(self):
        """test show user"""

        _data = u'bfs : api: user.show : {"username":"testuser1"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"]["username"] == 'testuser1')

    def test_5(self):
        """test show all and remove user"""

        _data = u'bfs : api: user.show.all : {}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"]["count"] == 1)
        self.assertTrue(len(msg_data["data"]["users"]) == 1)

        _data = u'bfs : api: user.new : {"username":"testuser2","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.show.all : {}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"]["count"] == 2)
        self.assertTrue(len(msg_data["data"]["users"]) == 2)

        _data = u'bfs : api: user.del : {"username":"testuser2"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.show.all : {}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"]["count"] == 1)
        self.assertTrue(len(msg_data["data"]["users"]) == 1)

    def test_6(self):
        """test user db access"""

        _data = u'bfs : api: user.dbaccess.grant : {"username":"testuser1","database":"ppme"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        # add same database again to test no duplicates added
        _data = u'bfs : api: user.dbaccess.grant : {"username":"testuser1","database":"ppme"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.dbaccess.grant : {"username":"testuser1","database":"gcm"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.dbaccess : {"username":"testuser1","database":"ppme"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"])

        _data = u'bfs : api: user.show : {"username":"testuser1"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(len(msg_data["data"]["databases"]) == 2)

        _data = u'bfs : api: user.dbaccess.revoke : {"username":"testuser1","database":"gcm"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.show : {"username":"testuser1"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(len(msg_data["data"]["databases"]) == 1)
        self.assertTrue(msg_data["data"]["databases"][0] == "ppme")

        # check bulk dbaccess operations
        _data = u'bfs : api: user.new : {"username":"testuser2","password":"12345678"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.all.dbaccess.grant : {"database":"gcm2"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.dbaccess : {"username":"testuser1","database":"gcm2"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"])

        _data = u'bfs : api: user.dbaccess : {"username":"testuser2","database":"gcm2"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"])

        _data = u'bfs : api: user.all.dbaccess.revoke : {"database":"gcm2"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u'bfs : api: user.dbaccess : {"username":"testuser1","database":"gcm2"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertFalse(msg_data["data"])

        _data = u'bfs : api: user.dbaccess : {"username":"testuser2","database":"gcm2"}'
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertFalse(msg_data["data"])

    def tearDown(self):
        self.socket.close()
        self.context.term()

class TestSessionService(unittest.TestCase):
    def setUp(self):
        configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        reader = json.load(open(configfile,"r"))

        self.endpoint = reader["bytengine"]["services"]["req_address"]
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)

    def test_1(self):
        """test session"""

        _data = u"bfs : api : session.new : %s" % json.dumps({"mode":"usermode","database":"db1","username":"user1","isroot":False})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        ticket = msg_data["data"]

        _data = u"bfs : api : session.get : %s" % json.dumps({"ticket":ticket})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        session_data = msg_data["data"]
        self.assertTrue(session_data["database"] == 'db1')
        self.assertTrue(session_data["mode"] == 'usermode')

        _data = u"bfs : api : session.update : %s" % json.dumps({"ticket":ticket,"db":"db1","username":"users'1"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : session.get : %s" % json.dumps({"ticket":ticket})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        session_data = msg_data["data"]
        self.assertTrue(session_data["username"] == "users'1")

    def tearDown(self):
        self.socket.close()
        self.context.term()

class TestServerManagement(unittest.TestCase):
    def setUp(self):
        configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        reader = json.load(open(configfile,"r"))

        self.endpoint = reader["bytengine"]["services"]["req_address"]
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)

    def test_1(self):
        """test rebuildserver"""
        _data = u"bfs : api : server.init :{} "
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

    def tearDown(self):
        self.socket.close()
        self.context.term()

class TestDatabaseManagement(unittest.TestCase):
    def setUp(self):
        configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        reader = json.load(open(configfile,"r"))

        self.endpoint = reader["bytengine"]["services"]["req_address"]
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)

    def test_1(self):
        """test makedatabase"""
        _data = u"bfs : api : db.make : %s" % json.dumps({"db":"test"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : db.make : %s" % json.dumps({"db":"test"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'error')

    def test_2(self):
        """test list databases"""
        _data = u"bfs : api : db.get.all : {}"
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue("test" in msg_data["data"])
        self.assertEqual(len(msg_data["data"]),1)

    def test_3(self):
        """test copy database"""
        _data = u"bfs : api : db.copy : %s" % json.dumps({"db_old":"test","db_new":"test2"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : db.get.all : {}"
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue("test2" in msg_data["data"])
        self.assertEqual(len(msg_data["data"]),2)

    def test_4(self):
        """test remove database"""
        _data = u"bfs : api : db.del : %s" % json.dumps({"db":"test2"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : db.get.all : {}"
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue("test" in msg_data["data"])
        self.assertFalse("test2" in msg_data["data"])
        self.assertEqual(len(msg_data["data"]),1)

    def tearDown(self):
        self.socket.close()
        self.context.term()

class TestContentManagement(unittest.TestCase):
    def setUp(self):
        configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        reader = json.load(open(configfile,"r"))

        self.endpoint = reader["bytengine"]["services"]["req_address"]
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)

    def test_1(self):
        """ test save node """
        node = Node()
        node.name = "tmp"
        node.content = {"user":"ricardo"}
        req = json.dumps({"data":node.serialize(),
                          "db":"test"})
        _data = u"bfs : api : node.save : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')

    def test_2(self):
        """ test find node """
        query = {"__header__.name":"tmp"}
        req = json.dumps({"query":query,
                          "db":"test",
                          "fields":[]})
        _data = u"bfs : api : node.get : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        node = Node(msg_data["data"])
        self.assertTrue(node.name == 'tmp')

    def test_3(self):
        """ test find all nodes """
        query = {"__header__.name":"/"}
        req = json.dumps({"query":query,
                          "db":"test",
                          "fields":["_id"]})
        _data = u"bfs : api : node.get.all : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        nodes = msg_data["data"]
        self.assertTrue(len(nodes) == 1)

    def test_4(self):
        """ test parent/child relationship """
        node = Node()
        node.name = "tmp2"
        node.content = {"user":"jason"}
        req = json.dumps({"data":node.serialize(),
                          "db":"test"})
        _data = u"bfs : api : node.save : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        child_id = str(msg_data["data"])

        # get parent node
        query = {"__header__.name":"/"}
        req = json.dumps({"query":query,
                          "db":"test",
                          "fields":["_id"]})
        _data = u"bfs : api : node.get : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        parent_id = str(msg_data["data"]["_id"])

        # create link
        req = json.dumps({"parent_docId":parent_id,
                          "child_docId":child_id,
                          "db":"test"})
        _data = u"bfs : api : subnode.add : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')

    def test_5(self):
        """ test get child nodes """
        # get parent node
        query = {"__header__.name":"/"}
        req = json.dumps({"query":query,
                          "db":"test",
                          "fields":["_id"]})
        _data = u"bfs : api : node.get : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        parent_id = str(msg_data["data"]["_id"])

        # get child nodes
        req = json.dumps({"docId":parent_id,
                          "db":"test",
                          "fields":[]})
        _data = u"bfs : api : subnode.get.all : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(len(msg_data["data"]) == 1)

    def test_6(self):
        """ test node copy """
        # get node
        query = {"__header__.name":"tmp"}
        req = json.dumps({"query":query,
                          "db":"test",
                          "fields":[]})
        _data = u"bfs : api : node.get : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        node = msg_data["data"]

        # get destination parent node
        query = {"__header__.name":"/"}
        req = json.dumps({"query":query,
                          "db":"test",
                          "fields":["_id"]})
        _data = u"bfs : api : node.get : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        parent_id = str(msg_data["data"]["_id"])

        # copy node
        query = {"__header__.name":"tmp"}
        req = json.dumps({"docId":node["_id"],
                          "parentId":parent_id,
                          "db":"test"})
        _data = u"bfs : api : node.copy : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')

        # get child nodes
        req = json.dumps({"docId":parent_id,
                          "db":"test",
                          "fields":[]})
        _data = u"bfs : api : subnode.get.all : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(len(msg_data["data"]) == 2)

        testlist = []
        for node in msg_data["data"]:
            testlist.append(node["user"])

        self.assertTrue("ricardo" in testlist)
        self.assertTrue("jason" in testlist)

    def test_7(self):
        """ test get node by path """
        req = json.dumps({"path":"/tmp",
                          "db":"test",
                          "fields":[]})
        _data = u"bfs : api : node.get.bypath : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        node = Node(msg_data["data"])
        self.assertTrue(node.name == 'tmp')
        self.assertTrue(node.content["user"] == 'ricardo')

    def test_8(self):
        """ test save attachment """
        attchmnt_f = os.path.join(os.path.abspath(os.path.dirname(__file__)),"pic1.jpg")
        req = json.dumps({"path":attchmnt_f,
                          "db":"test"})
        _data = u"bfs : api : binary.save : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        path = msg_data["data"]

        # get node
        req = json.dumps({"path":"/tmp",
                          "db":"test",
                          "fields":[]})
        _data = u"bfs : api : node.get.bypath : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        node = msg_data["data"]
        node["__header__"]["filepointer"] = path

        req = json.dumps({"data":node,
                          "db":"test"})
        _data = u"bfs : api : node.save : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')

    def test_9(self):
        """ test delete attachment """
        # get node
        req = json.dumps({"path":"/tmp",
                          "db":"test",
                          "fields":[]})
        _data = u"bfs : api : node.get.bypath : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        path = msg_data["data"]["__header__"]["filepointer"]

        req = json.dumps({"path":path})
        _data = u"bfs : api : binary.del : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertFalse(os.path.exists(path))

    def test_10(self):
        """ test delete node """
        # get node
        req = json.dumps({"path":"/",
                          "db":"test",
                          "fields":["_id"]})
        _data = u"bfs : api : node.get.bypath : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')
        _id = msg_data["data"]["_id"]

        req = json.dumps({"docId":_id,
                          "db":"test"})
        _data = u"bfs : api : node.del : %s" % req
        self.socket.send_string(_data)
        reply = self.socket.recv_string()
        msg_data = json.loads(reply)
        self.assertTrue(msg_data["status"] == 'ok')

    def tearDown(self):
        self.socket.close()
        self.context.term()

class TestCounters(unittest.TestCase):
    def setUp(self):
        configfile = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
        reader = json.load(open(configfile,"r"))

        self.endpoint = reader["bytengine"]["services"]["req_address"]
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.endpoint)

    def test_1(self):
        """test counter update"""
        _data = u"bfs : api : counter.update : %s" % json.dumps({"db":"test",
                                                                 "counter":"students",
                                                                 "action":"incr",
                                                                 "value":1})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        _current_val = msg_data["data"]
        self.assertTrue(_current_val == 1)

        _data = u"bfs : api : counter.get : %s" % json.dumps({"db":"test",
                                                              "counter":"students"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(_current_val == msg_data["data"])

        _data = u"bfs : api : counter.update : %s" % json.dumps({"db":"test",
                                                                 "counter":"students",
                                                                 "action":"decr",
                                                                 "value":1})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : counter.get : %s" % json.dumps({"db":"test",
                                                              "counter":"students"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"] == 0)

        _data = u"bfs : api : counter.update : %s" % json.dumps({"db":"test",
                                                                 "counter":"students",
                                                                 "action":"init",
                                                                 "value":-1})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : counter.get : %s" % json.dumps({"db":"test",
                                                              "counter":"students"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        self.assertTrue(msg_data["data"] == -1)

    def test_2(self):
        """test counter list"""
        _data = u"bfs : api : counter.update : %s" % json.dumps({"db":"test",
                                                                 "counter":"teachers",
                                                                 "action":"init",
                                                                 "value":5})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : counter.list : %s" % json.dumps({"db":"test"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        _result = msg_data["data"]
        self.assertTrue(len(_result) == 2)

    def test_3(self):
        """test counter clear"""
        _data = u"bfs : api : counter.clear : %s" % json.dumps({"db":"test",
                                                                "counter":"teachers"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')

        _data = u"bfs : api : counter.list : %s" % json.dumps({"db":"test"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertTrue(msg_data["status"] == 'ok')
        _result = msg_data["data"]
        self.assertTrue(len(_result) == 1)
        self.assertTrue(_result[0]["name"] == "students")

        _data = u"bfs : api : counter.get : %s" % json.dumps({"db":"test",
                                                              "counter":"teachers"})
        self.socket.send_string(_data)
        msg = self.socket.recv_string()
        msg_data = json.loads(msg)
        self.assertFalse(msg_data["status"] == 'ok')

    def tearDown(self):
        self.socket.close()
        self.context.term()

if __name__ == '__main__':
    #build test suite
    testsuite = unittest.TestSuite()
    
    # bfs tests
    testsuite.addTest(TestServerManagement("test_1"))

    #parser tests
    testsuite.addTest(TestParserService("test_1"))
    testsuite.addTest(TestParserService("test_2"))

    #security tests
    testsuite.addTest(TestSecurityService("test_1"))
    testsuite.addTest(TestSecurityService("test_2"))
    testsuite.addTest(TestSecurityService("test_3"))
    testsuite.addTest(TestSecurityService("test_4"))
    testsuite.addTest(TestSecurityService("test_5"))
    testsuite.addTest(TestSecurityService("test_6"))
    
    # session tests
    testsuite.addTest(TestSessionService("test_1"))
    
    testsuite.addTest(TestDatabaseManagement("test_1"))
    testsuite.addTest(TestDatabaseManagement("test_2"))
    testsuite.addTest(TestDatabaseManagement("test_3"))
    testsuite.addTest(TestDatabaseManagement("test_4"))
    
    testsuite.addTest(TestContentManagement("test_1"))
    testsuite.addTest(TestContentManagement("test_2"))
    testsuite.addTest(TestContentManagement("test_3"))
    testsuite.addTest(TestContentManagement("test_4"))
    testsuite.addTest(TestContentManagement("test_5"))
    testsuite.addTest(TestContentManagement("test_6"))
    testsuite.addTest(TestContentManagement("test_7"))
    testsuite.addTest(TestContentManagement("test_8"))
    testsuite.addTest(TestContentManagement("test_9"))
    testsuite.addTest(TestContentManagement("test_10"))
    
    # counter tests
    testsuite.addTest(TestCounters("test_1"))
    testsuite.addTest(TestCounters("test_2"))
    testsuite.addTest(TestCounters("test_3"))

    #run test suite
    unittest.TextTestRunner(verbosity=2).run(testsuite)