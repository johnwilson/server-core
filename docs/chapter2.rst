***********************************************
Installing Bytengine dependencies on CentOS 6.3
***********************************************
This guide will show you how to install Bytengine dependencies on a server running **CentOS 6.3**

The following software packages will be installed/built:

* python 2.7 (or higher)
* nginx (including 3rd party modules)
* mongodb
* redis
* zeromq

Specific python packages that will be installed are:

* setuptools
* tornado
* sphinx
* pymongo
* pyzmq
* redis
* pyparsing
* supervisor
* requests

.. note::
    This guide was tested with a 64bit instance of CentOS 6.3 (i.e. x86_64)
    

Step 1: Check your server's details
===================================

.. code-block:: bash

    cat /etc/redhat-release
    
    uname -a
    

Step 2: Install build and other dependencies
============================================

.. code-block:: bash
    
    yum update
    
    reboot
    
    yum install zlib-devel wget openssl-devel pcre pcre-devel sudo gcc curl \
    make autoconf automake gcc gdbm-devel readline-devel ncurses-devel \
    zlib-devel bzip2-devel sqlite-devel db4-devel openssl-devel tk-devel \
    bluez-libs-devel make pkgconfig libtool autoconf e2fsprogs-devel gcc-c++ \
    uuid-devel libuuid-devel uuid-c++ libuuid
    
    reboot
    

Step 3: Download required software source files
===============================================

.. code-block:: bash
    
    mkdir /tmp/downloads
    
    cd /tmp/downloads
    
    wget http://www.python.org/ftp/python/2.7.3/Python-2.7.3.tgz
    
    wget http://download.zeromq.org/zeromq-2.2.0.tar.gz
    
    wget http://peak.telecommunity.com/dist/ez_setup.py
    
    wget http://redis.googlecode.com/files/redis-2.4.17.tar.gz
    
    wget http://nginx.org/download/nginx-1.2.3.tar.gz
    
    wget http://www.grid.net.ru/nginx/download/nginx_upload_module-2.2.0.tar.gz
    
    wget -O nginx-upstream-fair-module.tar.gz http://github.com/gnosek/nginx-upstream-fair/tarball/master
    
We'll also download *init script* files for **nginx** and **redis** from Linode.com

.. code-block:: bash

    wget -O init-redis-rpm.sh http://library.linode.com/assets/631-redis-init-rpm.sh
    
    wget -O init-nginx-rpm.sh http://library.linode.com/assets/662-init-rpm.sh
    

Step 4: Install python 2.7
==========================
CentOS 6.3 comes with python 2.6 by default and Bytengine requires python 2.6 and above.
Python 2.7 will be installed alongside the preinstalled one so as not to cause any conflicts.

.. code-block:: bash
    
    cd /tmp/downloads
    
    tar xvzf Python-2.7.3.tgz
    
    cd Python-2.7.3
    
    ./configure --with-threads
    
    make
    
    make altinstall prefix=/opt/python_alt
    
    ln -sf /opt/python_alt/bin/python2.7 /usr/bin/python2.7
    

Step 5: Install zeromq 2.2
==========================

.. code-block:: bash

    cd /tmp/downloads
    
    tar xvzf zeromq-2.2.0.tar.gz
    
    cd zeromq-2.2.0
    
    ./configure
    
    make
    
    make install
    
    ldconfig
    

Step 6: Install redis
=====================

.. code-block:: bash

    cd /tmp/downloads
    
    tar xvzf redis-2.4.17.tar.gz
    
    cd redis-2.4.17
    
    make
    
    mkdir /opt/redis
    
    cp /tmp/downloads/redis-2.4.17/redis.conf /opt/redis/redis.conf.default
    
    cp /tmp/downloads/redis-2.4.17/src/redis-benchmark /opt/redis/
    
    cp /tmp/downloads/redis-2.4.17/src/redis-cli /opt/redis/
    
    cp /tmp/downloads/redis-2.4.17/src/redis-server /opt/redis/
    
    cp /tmp/downloads/redis-2.4.17/src/redis-check-aof /opt/redis/
    
    cp /tmp/downloads/redis-2.4.17/src/redis-check-dump /opt/redis/
    
    cp /opt/redis/redis.conf.default /opt/redis/redis.conf
    
    vi /opt/redis/redis.conf

.. note::
    Update the following in redis default configuration file:
    
    .. code-block:: bash
    
        daemonize yes
        pidfile /var/run/redis.pid
        logfile /var/log/redis.log
        
        port 6379
        bind 127.0.0.1
        timeout 300
        
        loglevel notice
        
        databases 16
    
        save 900 1
        save 300 10
        save 60 10000
        
        rdbcompression yes
        dbfilename dump.rdb
        
        dir /opt/redis/
        appendonly no
        
Save config file and proceed with installation

.. code-block:: bash

    cd /tmp/downloads
    
    useradd -M -r --home-dir /opt/redis redis
    
    mv init-redis-rpm.sh /etc/init.d/redis
    
    chmod +x /etc/init.d/redis
    
    chown -R redis:redis /opt/redis
    
    touch /var/log/redis.log
    
    chown redis:redis /var/log/redis.log
    
    /etc/init.d/redis start
    
Check redis instance by checking the log file and testing the redis cli

.. code-block:: bash
    
    cat /var/log/redis.log 

    /opt/redis/redis-cli
    
If everything is working add redis to startup programs

.. code-block:: bash
    
    chkconfig --add redis
    
    chkconfig redis on


Step 7: Install mongodb
=======================
Create a new mongodb repository

.. code-block:: bash
    
    vi /etc/yum.repos.d/10gen.repo
    
.. note::
    Add the following to the file:
    
    .. code-block:: bash
    
        [10gen]
        name=10gen Repository
        baseurl=http://downloads-distro.mongodb.org/repo/redhat/os/x86_64
        gpgcheck=0
        enabled=1

Save repo file and proceed with installation

.. code-block:: bash

    yum install mongo-10gen mongo-10gen-server
    
    /etc/init.d/mongod start
    
Test the mongodb installation by launching the mondb cli

.. code-block:: bash

    mongo
    
If everything is working add mongodb to startup programs

.. code-block:: bash
    
    chkconfig mongod on


Step 8: Install python modules
==============================

.. code-block:: bash

    cd /tmp/downloads
    
    python2.7 ez_setup.py
    
    ln -sf /opt/python_alt/bin/easy_install /usr/bin/easy_install2.7
    
    easy_install2.7 -Z -U pymongo
    
    easy_install2.7 -U pyparsing
    
    easy_install2.7 -U redis
    
    easy_install2.7 -U pyzmq
    
    easy_install2.7 -U tornado
    
    easy_install2.7 -U supervisor
    
    easy_install2.7 -U sphinx
    
    easy_install2.7 -U requests
    
    ln -sf /opt/python_alt/bin/supervisord /usr/bin/supervisord2.7
    
    ln -sf /opt/python_alt/bin/supervisorctl /usr/bin/supervisorctl2.7
    

Step 9: Install nginx
=====================

.. code-block:: bash

    cd /tmp/downloads
    
    tar xvzf nginx_upload_module-2.2.0.tar.gz
    
    tar xvzf nginx-upstream-fair-module.tar.gz
    
    mv gnosek-nginx-upstream-fair-xxx/ nginx-upstream-fair-module
    
    tar xvzf nginx-1.2.3.tar.gz
    
    cd nginx-1.2.3
    
    ./configure --prefix=/opt/nginx --user=nginx --group=nginx \
    --with-http_ssl_module --add-module=/tmp/downloads/nginx-upstream-fair-module \
    --add-module=/tmp/downloads/nginx_upload_module-2.2.0
    
    make
    
    make install
    
    useradd -M -r --shell /sbin/nologin --home-dir /opt/nginx nginx
    
    cd /tmp/downloads
    
    mv init-nginx-rpm.sh /etc/rc.d/init.d/nginx
    
    chmod +x /etc/rc.d/init.d/nginx
    
    /etc/init.d/nginx start
    
Check **nginx** with curl. If everything is working add **nginx** to startup programs

.. code-block:: bash

    curl http://127.0.0.1/
    
    chkconfig --add nginx
    
    chkconfig nginx on
    

Step 10: Configure IPTables firewall
====================================

.. code-block:: bash

    vi /etc/sysconfig/iptables

.. note::
    Add the following to the file to open ports **80** and **8500**:
    
    .. code-block:: bash
    
        -A RH-Firewall-1-INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT
        -A RH-Firewall-1-INPUT -m state --state NEW -m tcp -p tcp --dport 8500 -j ACCEPT
        
Save the file and restart IPTables and check ports

.. code-block:: bash

    service iptables restart
    
    netstat -tulpn | less
    
    iptables -L -n
