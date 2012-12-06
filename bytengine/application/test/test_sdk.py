import sys
import os
import json
import unittest

# add bytengine to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

from bytengine.application.core import sdk, common


class TestParserService(unittest.TestCase):
    def test_1(self):
        """test command line parser"""
        response = sdk.cmd_parsecommandline(command="makefile -p=/tmp/file1")
        self.assertTrue("command" in response)
        self.assertEqual("makefile", response["command"][0])

        # assert raises parsing error
        with self.assertRaises(common.BytengineError):
            response = sdk.cmd_parsecommandline(command=" -p=/tmp/file1")

    def test_2(self):
        """test bql parser"""
        response = sdk.cmd_parsebql(query="select('name') from ('/users')")
        self.assertIsNotNone(response)
        self.assertTrue("select" in response)
        self.assertTrue("from" in response)

        # assert raises parsing error
        with self.assertRaises(common.BytengineError):
            response = sdk.cmd_parsebql(query="select('name') from '/users'")

class TestSessionService(unittest.TestCase):
    def test_1(self):
        """test session"""
        ticket = sdk.cmd_createsession(mode="application",database="ppme",username="user1",isroot=False)
        self.assertIsNotNone(ticket)

        session_data = sdk.cmd_getsession(ticket=ticket)
        self.assertIsNotNone(session_data)
        self.assertTrue(session_data["database"] == 'ppme')

        isupdated = sdk.cmd_updatesession(ticket=ticket,database="db1")
        self.assertIsNotNone(session_data)
        self.assertTrue(isupdated)

        session_data = sdk.cmd_getsession(ticket=ticket)
        self.assertIsNotNone(session_data)
        self.assertTrue(session_data["database"] == 'db1')

class TestServerManagement(unittest.TestCase):
    def test_1(self):
        """test rebuildserver"""
        r = sdk.cmd_rebuildserver()
        self.assertTrue(r)

class TestDatabaseManagement(unittest.TestCase):
    def test_1(self):
        """test makedatabase"""
        r = sdk.cmd_makedatabase(db="test")
        self.assertTrue(r)

        # duplicate
        with self.assertRaises(common.BytengineError):
            r = sdk.cmd_makedatabase(db="test")

    def test_2(self):
        """test list databases"""
        r = sdk.cmd_listdatabases()
        self.assertTrue("test" in r)
        self.assertEqual(len(r),1)

    def test_3(self):
        """test copy database"""
        r = sdk.cmd_copydatabase(db_old="test", db_new="test2")
        self.assertTrue(r)

        r = sdk.cmd_listdatabases()
        self.assertTrue("test2" in r)
        self.assertEqual(len(r),2)

    def test_4(self):
        """test remove database"""
        r = sdk.cmd_removedatabase(db="test2")
        self.assertTrue(r)

        r = sdk.cmd_listdatabases()
        self.assertTrue("test" in r)
        self.assertFalse("test2" in r)
        self.assertEqual(len(r),1)

class TestContentManagement(unittest.TestCase):
    def test_1(self):
        """ test save node """
        node = common.File()
        node.name = "tmp"
        node.content = {"user":"ricardo"}
        r = sdk.cmd_savenode(data=node.serialize(), db="test")
        self.assertTrue(r)

    def test_2(self):
        """ test find node """
        query = {"__header__.name":"tmp"}
        r = sdk.cmd_getnode(query=query,db="test",fields=[])
        node = sdk.Node(r)
        self.assertTrue(node.name == 'tmp')

    def test_3(self):
        """ test find all nodes """
        query = {"__header__.name":"/"}
        r = sdk.cmd_getnodelist(query=query,db="test",fields=["_id"])
        self.assertTrue(len(r) == 1)

    def test_4(self):
        """ test parent/child relationship """
        node = common.File()
        node.name = "tmp2"
        node.content = {"user":"jason"}
        r = sdk.cmd_savenode(data=node.serialize(), db="test")
        self.assertTrue(r)
        child_id = r

        # get parent node
        query = {"__header__.name":"/"}
        r = sdk.cmd_getnode(query=query,db="test",fields=["_id"])
        parent_id = r["_id"]

        # create link
        req = json.dumps({"parent_docId":parent_id,
                          "child_docId":child_id,
                          "db":"test"})
        r = sdk.cmd_addchild(parent_docId=parent_id, child_docId=child_id,db="test")
        self.assertTrue(r)

    def test_5(self):
        """ test get child nodes """
        # get parent node
        query = {"__header__.name":"/"}
        r = sdk.cmd_getnode(query=query,db="test",fields=["_id"])
        parent_id = r["_id"]

        # get child nodes
        r = sdk.cmd_childnodes(docId=parent_id,db="test",fields=[])
        self.assertTrue(len(r) == 1)

    def test_6(self):
        """ test node copy """
        # get node
        query = {"__header__.name":"tmp"}
        r = sdk.cmd_getnode(query=query,db="test",fields=[])
        node_id = r["_id"]

        # get destination parent node
        query = {"__header__.name":"/"}
        r = sdk.cmd_getnode(query=query,db="test",fields=["_id"])
        parent_id = r["_id"]

        # copy node
        query = {"__header__.name":"tmp"}
        r = sdk.cmd_copynode(docId=node_id,parentId=parent_id,db="test")
        self.assertTrue(r)

        # get child nodes
        r = sdk.cmd_childnodes(docId=parent_id,db="test",fields=[])
        self.assertTrue(len(r) == 2)

        testlist = []
        for node in r:
            testlist.append(node["user"])

        self.assertTrue("ricardo" in testlist)
        self.assertTrue("jason" in testlist)

    def test_7(self):
        """ test get node by path """
        r = sdk.cmd_getnode_bypath(path="/tmp",db="test",fields=[])
        node = sdk.Node(r)
        self.assertTrue(node.name == 'tmp')
        self.assertTrue(node.content["user"] == 'ricardo')

    def test_8(self):
        """ test save attachment """
        attchmnt_f = os.path.join(os.path.abspath(os.path.dirname(__file__)),"pic1.jpg")
        r = sdk.cmd_saveattachment(path=attchmnt_f,db="test")
        self.assertTrue(r)
        path = r

        # get node
        r = sdk.cmd_getnode_bypath(path="/tmp",db="test",fields=[])
        node = r
        node["__header__"]["filepointer"] = path

        r = sdk.cmd_savenode(data=node, db="test")
        self.assertTrue(r)

    def test_9(self):
        """ test delete attachment """
        # get node
        r = sdk.cmd_getnode_bypath(path="/tmp",db="test",fields=[])
        path = r["__header__"]["filepointer"]

        r = sdk.cmd_removeattachment(path=path)
        self.assertTrue(r)
        self.assertFalse(os.path.exists(path))

    def test_10(self):
        """ test find """
        # get node
        query = "select('user') from('/') where $eq('user','ricardo')"
        r = sdk.cmd_find(query=query,db="test")
        self.assertTrue(len(r) == 1)
        self.assertTrue(r[0]["content"]["user"] == "ricardo")

        # get all nodes
        query = "select('user') from('/')"
        r = sdk.cmd_find(query=query,db="test")
        self.assertTrue(len(r) == 2)

    def test_11(self):
        """ test delete node """
        # get node
        r = sdk.cmd_getnode_bypath(path="/",db="test",fields=["_id"])
        _id = r["_id"]

        r = sdk.cmd_removenode(docId=_id,db="test")
        self.assertTrue(r)

class TestSecurityService(unittest.TestCase):
    def test_1(self):
        """test clear all users"""
        r = sdk.cmd_removealluser()
        self.assertTrue(r)

    def test_2(self):
        """test new user"""
        # short password error
        with self.assertRaises(common.BytengineError):
            r = sdk.cmd_newuser(username="testuser1",password="admin")

        r = sdk.cmd_newuser(username="testuser1",password="12345678")
        self.assertTrue(r)

    def test_3(self):
        """test authenticate user"""
        r = sdk.cmd_authenticate(username="testuser1",password="12345678")
        self.assertTrue(r)

        # change password
        r = sdk.cmd_updatepasswd(username="testuser1",password="910111213")
        self.assertTrue(r)

        with self.assertRaises(common.BytengineError):
            r = sdk.cmd_authenticate(username="testuser1",password="12345678")

        r = sdk.cmd_authenticate(username="testuser1",password="910111213")
        self.assertTrue(r)

        # activate / deactivate test
        r = sdk.cmd_deactivateuser(username="testuser1")
        self.assertTrue(r)

        # authentication fail
        with self.assertRaises(common.BytengineError):
            r = sdk.cmd_authenticate(username="testuser1",password="910111213")

        r = sdk.cmd_activateuser(username="testuser1")
        self.assertTrue(r)

        r = sdk.cmd_authenticate(username="testuser1",password="910111213")
        self.assertTrue(r)

    def test_4(self):
        """test show user"""
        r = sdk.cmd_getuser(username="testuser1")
        self.assertTrue(r["username"] == 'testuser1')

    def test_5(self):
        """test show all and remove user"""
        r = sdk.cmd_getalluser()
        self.assertTrue(r["count"] == 1)
        self.assertTrue(len(r["users"]) == 1)

        r = sdk.cmd_newuser(username="testuser2",password="12345678")
        self.assertTrue(r)

        r = sdk.cmd_getalluser()
        self.assertTrue(r["count"] == 2)
        self.assertTrue(len(r["users"]) == 2)

        r = sdk.cmd_removeuser(username="testuser2")
        self.assertTrue(r)

        r = sdk.cmd_getalluser()
        self.assertTrue(r["count"] == 1)
        self.assertTrue(len(r["users"]) == 1)

    def test_6(self):
        """test user db access"""
        r = sdk.cmd_grantdbaccess(username="testuser1",database="ppme")
        self.assertTrue(r)

        # add same database again to test no duplicates added
        r = sdk.cmd_grantdbaccess(username="testuser1",database="ppme")
        self.assertTrue(r)

        r = sdk.cmd_grantdbaccess(username="testuser1",database="gcm")
        self.assertTrue(r)

        r = sdk.cmd_hasdbaccess(username="testuser1",database="ppme")
        self.assertTrue(r)

        r = sdk.cmd_getuser(username="testuser1")
        self.assertTrue(len(r["databases"]) == 2)

        r = sdk.cmd_revokedbaccess(username="testuser1",database="gcm")
        self.assertTrue(r)

        r = sdk.cmd_getuser(username="testuser1")
        self.assertTrue(len(r["databases"]) == 1)
        self.assertTrue(r["databases"][0] == "ppme")

        # check bulk dbaccess operations
        r = sdk.cmd_newuser(username="testuser2",password="12345678")
        self.assertTrue(r)

        r = sdk.cmd_grantalldbaccess(database="gcm2")
        self.assertTrue(r)

        r = sdk.cmd_hasdbaccess(username="testuser1",database="gcm2")
        self.assertTrue(r)

        r = sdk.cmd_hasdbaccess(username="testuser2",database="gcm2")
        self.assertTrue(r)

        r = sdk.cmd_revokealldbaccess(database="gcm2")
        self.assertTrue(r)

        r = sdk.cmd_hasdbaccess(username="testuser1",database="gcm2")
        self.assertFalse(r)

        r = sdk.cmd_hasdbaccess(username="testuser2",database="gcm2")
        self.assertFalse(r)

class TestCounters(unittest.TestCase):
    def test_1(self):
        """test counter update"""
        r = sdk.cmd_counter_incr(db="test", value=1, counter="students")
        _current_val = r
        self.assertTrue(_current_val == 1)

        r = sdk.cmd_counter_get(db="test", counter="students")
        self.assertTrue(_current_val == r)

        sdk.cmd_counter_decr(db="test", value=1, counter="students")
        r = sdk.cmd_counter_get(db="test", counter="students")
        self.assertTrue(r == 0)

        sdk.cmd_counter_init(db="test", value=-1, counter="students")
        r = sdk.cmd_counter_get(db="test", counter="students")
        self.assertTrue(r == -1)

    def test_2(self):
        """test counter list"""
        sdk.cmd_counter_init(db="test", value=5, counter="teachers")
        r = sdk.cmd_counter_list(db="test")
        self.assertTrue(len(r) == 2)

    def test_3(self):
        """test counter clear"""
        sdk.cmd_counter_clear(db="test", counter="teachers")
        r = sdk.cmd_counter_list(db="test")
        self.assertTrue(len(r) == 1)
        self.assertTrue(r[0]["name"] == "students")

        # fail
        with self.assertRaises(common.BytengineError):
            r = sdk.cmd_counter_get(db="test", counter="teachers")

if __name__ == '__main__':
    #build test suite
    testsuite = unittest.TestSuite()

    #parser tests
    testsuite.addTest(TestParserService("test_1"))
    testsuite.addTest(TestParserService("test_2"))

    # server management tests
    testsuite.addTest(TestServerManagement("test_1"))

    # session tests
    testsuite.addTest(TestSessionService("test_1"))

    # bfs tests
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
    testsuite.addTest(TestContentManagement("test_11"))

    #security tests
    testsuite.addTest(TestSecurityService("test_1"))
    testsuite.addTest(TestSecurityService("test_2"))
    testsuite.addTest(TestSecurityService("test_3"))
    testsuite.addTest(TestSecurityService("test_4"))
    testsuite.addTest(TestSecurityService("test_5"))
    testsuite.addTest(TestSecurityService("test_6"))

    # counter tests
    testsuite.addTest(TestCounters("test_1"))
    testsuite.addTest(TestCounters("test_2"))
    testsuite.addTest(TestCounters("test_3"))

    #run test suite
    unittest.TextTestRunner(verbosity=2).run(testsuite)