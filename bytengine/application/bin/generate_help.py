#!/usr/bin/env python

import sys
import os
import json
import sqlite3

from docutils import core
from docutils.writers.html4css1 import Writer
from docutils.utils import SystemMessage

# add bytengine to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..","..")))

# get commands repository file
repo_f = os.path.join(os.path.dirname(__file__),"..","conf","commandrepository.json")
repo_reader = json.load(open(repo_f,"r"))

# help database file
config_f = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
config_reader = json.load(open(config_f,"r"))
db_f = os.path.join(os.path.dirname(__file__),"..","core",config_reader["bytengine"]["help_database"])

conn = sqlite3.connect(db_f)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS tbl_help")
cursor.execute("CREATE TABLE tbl_help (Id INTEGER PRIMARY KEY, Namespace TEXT, Command TEXT, Help_Raw TEXT, Help_Html TEXT)")

for namespace in repo_reader:
    # get class
    _module = __import__(repo_reader[namespace]["module"], fromlist=[repo_reader[namespace]["class"]])
    _class = getattr(_module,repo_reader[namespace]["class"])
    
    # generate help
    for cmd in repo_reader[namespace]["commands"]:
        _alias = cmd
        print _alias
        _function_name = repo_reader[namespace]["commands"][cmd]["function"]
        _showhelp = repo_reader[namespace]["commands"][cmd]["showhelp"]
        if _showhelp:            
            _function = getattr(_class,_function_name)
            cmd_help = _function.__doc__
            if not cmd_help:
                cmd_help = "**Help not generated for '{command}'**"
            # format
            cmd_help = cmd_help.format(command=_alias)
            
            # format doctrings to html
            cmd_help_html = ""
            try:
                tmp = core.publish_parts(cmd_help, writer=Writer())["html_body"]
                cmd_help_html = '<br/>'.join(tmp.split('\n')[1:-2])
            except Exception, e:
                cmd_help_html = "<p>Help not generated</p>"
                
            # add row to table
            row = (namespace,_alias,cmd_help,cmd_help_html)
            cursor.execute("INSERT INTO tbl_help VALUES(null,?,?,?,?)",row)

conn.commit()
cursor.close()
