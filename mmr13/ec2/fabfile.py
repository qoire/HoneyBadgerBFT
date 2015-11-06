from __future__ import with_statement
from fabric.api import *
from fabric.operations import put, get
from fabric.contrib.console import confirm
from fabric.contrib.files import append
import time

@parallel
def host_type():
    run('uname -s')

@parallel
def cloneRepo():
    run('git clone https://github.com/amiller/HoneyBadgerBFT.git')

@parallel
def install_dependencies():
    sudo('apt-get update')
    sudo('apt-get -y install python-gevent')
    sudo('apt-get -y install git')
    sudo('apt-get -y install subversion')
    sudo('apt-get -y install python-socksipy')
    sudo('apt-get -y install python-pip')
    sudo('apt-get -y install python-dev')
    sudo('apt-get -y install dtach')
    sudo('apt-get -y install python-gmpy2')
    sudo('pip install pycrypto')
    sudo('pip install ecdsa')

@parallel
def stopProtocols():
    with settings(warn_only=True):
        run('killall python')
        run('killall dtach')
        run('killall server.py')

@parallel
def removeHosts():
    run('rm ~/hosts')

@parallel
def writeHosts():
    put('./hosts', '~/')
    #append('~/hosts', open('hosts','r').read().split('\n'))

@parallel
def fetchLogs():
    get('~/HoneyBadgerBFT/mmr13/msglog.TorMultiple',
        'logs/%(host)s' + time.strftime(time.gmtime()) + '.log')

@parallel
def syncKeys():
    put('./keys', '~/')
    put('./ecdsa_keys', '~/')

@parallel
def runProtocol():
    with cd('~/HoneyBadgerBFT/mmr13'):
        run('python honest_party_test_EC2.py ~/hosts ~/keys ~/ecdsa_keys')

@parallel
def checkout():
    run('svn checkout --no-auth-cache --username aluex --password JkJ-3pc-s3Y-prp https://subversion.assembla.com/svn/ktc-scratch/')

@parallel
def svnUpdate():
    with settings(warn_only=True):
        if run('test -d ktc-scratch').failed:
            run('svn checkout  --no-auth-cache --username aluex --password JkJ-3pc-s3Y-prp https://subversion.assembla.com/svn/ktc-scratch/')
    with cd('~/ktc-scratch'):
        run('svn up  --no-auth-cache --username aluex --password JkJ-3pc-s3Y-prp')

@parallel
def svnClean():
    with settings(warn_only=True):
        if run('test -d ktc-scratch').failed:
            run('svn checkout --username aluex --password JkJ-3pc-s3Y-prp https://subversion.assembla.com/svn/ktc-scratch/')
    with cd('~/ktc-scratch'):
        run('svn cleanup')

@parallel
def makeExecutable():
    with cd('~/ktc-scratch'):
        run('chmod +x server.py')

# http://stackoverflow.com/questions/8775598/start-a-background-process-with-nohup-using-fabric
def runbg(cmd, sockname="dtach"):  
    return run('dtach -n `mktemp -u /tmp/%s.XXXX` %s'  % (sockname,cmd))

@parallel
def startPBFT(): ######## THIS SHOULD BE CALLED IN REVERSED HOST ORDER
    with cd('~/ktc-scratch'):
        runbg('python server.py')
        #run('sleep 10')

def startClient():
    with cd('~/ktc-scratch'):
        #batch_size = 1024
        #batch_size = 2048
        #batch_size = 4096
        #batch_size = 8192
        batch_size = 16384
        #batch_size = 65536
        run('python gen_requests.py 1000 %d' % (batch_size,))
        run('python client.py 40')
        run('python parse_client_log.py %d' % (batch_size,))

def git_pull():
    with settings(warn_only=True):
        if run('test -d HoneyBadgerBFT').failed:
            run('git clone https://github.com/amiller/HoneyBadgerBFT.git')
    with cd('~/HoneyBadgerBFT'):
        run('git checkout another-dev')
        run('git pull')
