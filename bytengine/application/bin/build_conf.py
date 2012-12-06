import os
import json
from jinja2 import FileSystemLoader, Environment

# settings
bytengine_conf = os.path.join(os.path.dirname(__file__),"..","conf","config.json")
configreader = json.load(open(bytengine_conf,"r"))
tmp_attch_dir = configreader["services"]["bfs"]["attachments_dir"]


ATTACHMENTS_DIR_NAME = os.path.basename(tmp_attch_dir)
ATTACHMENTS_DIR_ROOT = os.path.dirname(tmp_attch_dir)
USER = "fiifi"
ROOT_DIR = "/home/fiifi/Documents/Code/bytengine_project"
PYTHON = "python2.7"
tornado_servers = 1
webworker_servers = 1
parser_servers = 1
bfs_servers = 1
corecommand_servers = 1
email_servers = 1
emailcheck_servers = 1

datasource = {"ROOT_DIR":ROOT_DIR,
              "USER":USER,
              "ATTACHMENTS_DIR_NAME":ATTACHMENTS_DIR_NAME,
              "ATTACHMENTS_DIR_ROOT":ATTACHMENTS_DIR_ROOT,
              "PYTHON":PYTHON,
              "tornado_servers":[],
              "webworker_servers":[],
              "parser_servers":[],
              "bfs_servers":[],
              "email_servers":[],
              "emailcheck_servers":[],
              "corecommand_servers":[]}

for i in range(0,tornado_servers):
    datasource["tornado_servers"].append({"port":"800%s" % i})
    
for i in range(0,webworker_servers):
    datasource["webworker_servers"].append({"id":i+1})
    
for i in range(0,parser_servers):
    datasource["parser_servers"].append({"id":i+1})
    
for i in range(0,bfs_servers):
    datasource["bfs_servers"].append({"id":i+1})
    
for i in range(0,email_servers):
    datasource["email_servers"].append({"id":i+1})
    
for i in range(0,emailcheck_servers):
    datasource["emailcheck_servers"].append({"id":i+1})
    
for i in range(0,corecommand_servers):
    datasource["corecommand_servers"].append({"id":i+1})
    
# load Jinja
loader = FileSystemLoader(os.path.join(ROOT_DIR,"bytengine","application","conf"))
env = Environment(loader=loader)

# build supervisord conf
supervisord_template = env.get_template("supervisord.conf.jinja")
out_file = os.path.join(ROOT_DIR,"bytengine","application","conf","supervisord.conf")
f = open(out_file,"w+")
f.write(supervisord_template.render(**datasource))
f.close()

# build nginx conf
nginx_template = env.get_template("nginx.conf.jinja")
out_file = os.path.join(ROOT_DIR,"bytengine","application","conf","nginx.conf")
f = open(out_file,"w+")
f.write(nginx_template.render(**datasource))
f.close()
