import sys
import os
import json
import unittest

# add bytengine to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

from bytengine.application.core import common, sdk

class TestServerManagement(unittest.TestCase):
    def test_1(self):
        """test server management"""

        # login admin
        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc('rebuild', session=_session)
        self.assertTrue(r["status"] == "ok")

        # re-login admin because all sessions would have been cleared
        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc('makedb test', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('alldbs', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 1)

        r = sdk.command_rpc('copydb test test2', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('alldbs', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 2)

        r = sdk.command_rpc('dropdb test2', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('alldbs', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 1)
        self.assertTrue(r["data"][0] == "test")

class TestUserManagement(unittest.TestCase):
    def test_1(self):
        """test user login"""

        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc("login -u=admins -p=admin --usermode")
        self.assertFalse(r["status"] == "ok")

    def test_2(self):
        """test user creation"""

        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]
        
        # remove all users
        r = sdk.command_rpc('userdel "*"', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('useradd "user1" -p=password', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('userget "user1"', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"]["username"] == 'user1')

        r = sdk.command_rpc('userall', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"]["count"] == 1)

        # test new user login
        r = sdk.command_rpc('login -u="user1" -p="password" --usermode')
        self.assertTrue(r["status"] == 'ok')

    def test_3(self):
        """test user password update"""

        # login admin
        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc('passwd user1 password2', session=_session)
        self.assertTrue(r["status"] == 'ok')

        # test new user login
        r = sdk.command_rpc('login -u="user1" -p="password" --usermode')
        self.assertFalse(r["status"] == 'ok')

        r = sdk.command_rpc('login -u="user1" -p="password2" --usermode')
        self.assertTrue(r["status"] == 'ok')

        # relogin admin
        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        # disable user account
        r = sdk.command_rpc('svraccess user1 -b', session=_session)
        self.assertTrue(r["status"] == 'ok')

        r = sdk.command_rpc('login -u="user1" -p="password2" --usermode')
        self.assertFalse(r["status"] == 'ok')

        # enable user account
        r = sdk.command_rpc('svraccess user1 -a', session=_session)
        self.assertTrue(r["status"] == 'ok')

        r = sdk.command_rpc('login -u="user1" -p="password2" --usermode')
        self.assertTrue(r["status"] == 'ok')
        _session = r["data"]["ticket"]

        # test whoami
        r = sdk.command_rpc('whoami', session=_session)
        self.assertTrue(r["status"] == 'ok')
        self.assertTrue(r["data"] == 'user1')

        r = sdk.command_rpc('whoami -a', session=_session)
        self.assertTrue(r["status"] == 'ok')
        self.assertTrue(r["data"]["username"] == 'user1')

    def test_4(self):
        """test user db access"""

        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc('dbaccess "user1" "test" -a', session=_session)
        self.assertTrue(r["status"] == 'ok')

        r = sdk.command_rpc('dbaccess "user1" "test2" -a', session=_session)
        self.assertTrue(r["status"] == 'ok')

        r = sdk.command_rpc('userget "user1"', session=_session)
        self.assertTrue(r["status"] == 'ok')
        self.assertTrue("test" in r["data"]["databases"])
        self.assertTrue("test2" in r["data"]["databases"])

        r = sdk.command_rpc("login -u=user1 -p=password2 --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc('alldbs', session=_session)
        self.assertTrue(r["status"] == 'ok')
        self.assertTrue(len(r['data']) == 2)
        self.assertTrue("test" in r['data'])

        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc('dbaccess "user1" "test2" -r', session=_session)
        self.assertTrue(r["status"] == 'ok')

        r = sdk.command_rpc('userget "user1"', session=_session)
        self.assertTrue(r["status"] == 'ok')
        self.assertFalse("test2" in r["data"]["databases"])
        self.assertTrue("test" in r["data"]["databases"])

    def test_5(self):
        """test session database change"""
        r = sdk.command_rpc("login -u=user1 -p=password2 --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc("whichdb", session=_session)
        self.assertTrue(len(r["data"]) == 0)

        r = sdk.command_rpc("selectdb test", session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc("selectdb test2", session=_session)
        self.assertFalse(r["status"] == "ok")

        r = sdk.command_rpc("whichdb", session=_session)
        self.assertTrue(r["data"] == u"test")

    def test_6(self):
        """test remove user"""

        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]

        r = sdk.command_rpc('userdel "user1"', session=_session)
        self.assertTrue(r["status"] == 'ok')

        r = sdk.command_rpc('userall', session=_session)
        self.assertTrue(r["status"] == 'ok')
        self.assertTrue(r["data"]["count"] == 0)

class TestCounter(unittest.TestCase):
    def test_1(self):
        """test counter"""

        # login admin and create user1
        r = sdk.command_rpc("login -u=admin -p=admin --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]
        r = sdk.command_rpc('useradd "user1" -p=password', session=_session)
        self.assertTrue(r["status"] == "ok")
        r = sdk.command_rpc('dbaccess user1 test -a', session=_session)
        self.assertTrue(r["status"] == "ok")

        # login user1
        r = sdk.command_rpc("login -u=user1 -p=password --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]
        # select database
        r = sdk.command_rpc("selectdb test", session=_session)
        self.assertTrue(r["status"] == "ok")

        # create counter from init
        r = sdk.command_rpc('counter students init 5', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == 5)

        r = sdk.command_rpc('counterget students', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == 5)

        # create counter from incr
        r = sdk.command_rpc('counter classrooms incr 1', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == 1)

        r = sdk.command_rpc('counterget classrooms', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == 1)

        # decrement counter
        r = sdk.command_rpc('counter students decr 2', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == 3)

        r = sdk.command_rpc('counterget students', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == 3)

        r = sdk.command_rpc('counterall', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 2)

        r = sdk.command_rpc('counterdel classrooms', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == 1)

class TestContentManagent(unittest.TestCase):
    def test_1(self):
        """test content management"""

        # login admin and create user1
        r = sdk.command_rpc("login -u=user1 -p=password --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]
        r = sdk.command_rpc('selectdb test', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkdir /var', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkdir /var/www', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkfile /var/www/index.html {}', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('modfile /var/www/index.html {"title":"welcome","body":"Hello world!"}', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('cp /var/www/index.html /var/www -r="about.html"', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('rename /var/www/index.html home.html', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('modfile /var/www/about.html -o {"title":"about us"}', session=_session)
        self.assertTrue(r["status"] == "ok")
        
        r = sdk.command_rpc('mfset "/var/www/home.html" "/var/www/about.html" {"author":"john","date":"today"}', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('viewfile /var/www/about.html', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"]["content"]["title"] == "about us")
        self.assertTrue(r["data"]["content"]["author"] == "john")
        self.assertTrue(r["data"]["content"]["date"] == "today")
        
        r = sdk.command_rpc('viewfile /var/www/home.html', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"]["content"]["author"] == "john")
        self.assertTrue(r["data"]["content"]["date"] == "today")
        
        r = sdk.command_rpc('mfunset "/var/www/home.html" "/var/www/about.html" ["author"]', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('viewfile /var/www/about.html', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertFalse("author" in r["data"]["content"])
        
        r = sdk.command_rpc('viewfile /var/www/home.html', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertFalse("author" in r["data"]["content"])

        r = sdk.command_rpc('mkdir /var/www/static', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkfile /var/www/static/main.css {}', session=_session)
        self.assertTrue(r["status"] == "ok")

        f = open("/tmp/test.css","w")
        f.write("body{ background-color: #ffffff }")
        f.close()
        r = sdk.command_rpc('upload /var/www/static/main.css', session=_session, attachment="/tmp/test.css")
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkpublic /var/www/static/main.css', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('info /var/www/static/main.css', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"]["name"] == "main.css")
        self.assertTrue(r["data"]["attachment"])
        self.assertTrue(r["data"]["public"])

        r = sdk.command_rpc('attachdel /var/www/static/main.css', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkprivate /var/www/static/main.css', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('info /var/www/static/main.css', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"]["name"] == "main.css")
        self.assertFalse(r["data"]["attachment"])
        self.assertFalse(r["data"]["public"])

        r = sdk.command_rpc('mkdir /backup', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mv /var/www /backup', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('rm /var -r', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('info /backup/www/static/main.css', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"]["name"] == "main.css")

        r = sdk.command_rpc('ls /', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]["dirs"]) == 1)
        self.assertTrue("backup" in r["data"]["dirs"])

class TestContentSearch(unittest.TestCase):
    def test_1(self):
        """test content search data"""

        vehicles = []
        vehicles.append({"make":"honda","model":"civic","cost":27000,"year":2005})
        vehicles.append({"make":"Honda","model":"accord","cost":35000,"year":2011})
        vehicles.append({"make":"kia","model":"sportage","cost":28000,"year":2012})
        vehicles.append({"make":"nissan","model":"patrol","cost":64000,"year":2005,"colour":"black"})

        # login user1
        r = sdk.command_rpc("login -u=user1 -p=password --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]
        r = sdk.command_rpc('selectdb test', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkdir /cars', session=_session)
        self.assertTrue(r["status"] == "ok")

        # create counter from incr
        r = sdk.command_rpc('counter vehicles init 0', session=_session)
        self.assertTrue(r["status"] == "ok")

        for vehicle in vehicles:
            r = sdk.command_rpc('counter vehicles incr', session=_session)
            id = r["data"]
            cmd_text = 'mkfile /cars/veh_{id} {data}'.format(id=id, data=json.dumps(vehicle))
            r = sdk.command_rpc(cmd_text, session=_session)
            self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('ls /cars', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]["files"]) == len(vehicles))

    def test_2(self):
        """test content search"""

        # login user1
        r = sdk.command_rpc("login -u=user1 -p=password --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]
        r = sdk.command_rpc('selectdb test', session=_session)
        self.assertTrue(r["status"] == "ok")

        # find all hondas
        q = "bql Select('make','model') From('/cars') Where $eq('make','honda')"
        r = sdk.command_rpc(q, session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 1)
        
        # using regex search
        q = "bql Select('make','model') From('/cars') Where $regex('make','[h|H]onda')"
        r = sdk.command_rpc(q, session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 2)
        

        # find all cars costing more than 30000
        q = "bql Select('make','model') From('/cars') Where $gt('cost',30000)"
        r = sdk.command_rpc(q, session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 2)
        for item in r["data"]:
            self.assertTrue(item["content"]["make"] in ["Honda","nissan"])

        # find all cars that have colour listed
        q = "bql Select('make','model') From('/cars') Where $exists('colour')"
        r = sdk.command_rpc(q, session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(len(r["data"]) == 1)
        self.assertTrue(r["data"][0]["content"]["make"] == "nissan")        

class TestTemplateRenderer(unittest.TestCase):
    def test_1(self):
        """test template renderer"""

        # create template file
        f = open("/tmp/test.jinja","w")
        f.write("{{ greeting }} {{ name }}")
        f.close()

        # login user1
        r = sdk.command_rpc("login -u=user1 -p=password --usermode")
        self.assertTrue(r["status"] == "ok")
        _session = r["data"]["ticket"]
        r = sdk.command_rpc('selectdb test', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mkfile /template_test {"name":"Jason Bourne"}', session=_session)        
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('upload /template_test', session=_session, attachment="/tmp/test.jinja")
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mktemplate /template_test {"greeting":"Welcome"}', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == "Welcome Jason Bourne")

        r = sdk.command_rpc('mkfile /template_test_data {"name":"Jennifer Lopez"}', session=_session)
        self.assertTrue(r["status"] == "ok")

        r = sdk.command_rpc('mktemplate /template_test -d="/template_test_data" {"greeting":"Welcome"}', session=_session)
        self.assertTrue(r["status"] == "ok")
        self.assertTrue(r["data"] == "Welcome Jennifer Lopez")

if __name__ == '__main__':
    #build test suite
    testsuite = unittest.TestSuite()

    testsuite.addTest(TestServerManagement("test_1"))

    testsuite.addTest(TestUserManagement("test_1"))
    testsuite.addTest(TestUserManagement("test_2"))
    testsuite.addTest(TestUserManagement("test_3"))
    testsuite.addTest(TestUserManagement("test_4"))
    testsuite.addTest(TestUserManagement("test_5"))
    testsuite.addTest(TestUserManagement("test_6"))
    
    testsuite.addTest(TestCounter("test_1"))
    
    testsuite.addTest(TestContentManagent("test_1"))
    
    testsuite.addTest(TestContentSearch("test_1"))
    testsuite.addTest(TestContentSearch("test_2"))
    
    testsuite.addTest(TestTemplateRenderer("test_1"))

    #run test suite
    unittest.TextTestRunner(verbosity=2).run(testsuite)