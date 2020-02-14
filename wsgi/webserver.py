""" starts a python webserver primary purpose is to simplify debuging within the python module
"""
from optparse import OptionParser as op
from sys import argv

##befor calling import module must add the path
## where pyUweb.py file is located and the
## path(s) to website applications 
from sys import path
path.append('/home/MAGWERKS.COM/justin/github/pyUweb/')
#path.append('/home/justin/git_hub/pyUweb/')

import importlib
#import wsgiserver
from  waitress import serve
from config import APPSTACK as _as


def parse_args(p_argv):

    _paser = op()
    _paser.add_option('-p', '--port', dest='port', default=8080,  type='int',
        help='port number to bind to', metavar='PORT')
    _paser.add_option('-a', '--ipaddress', dest='ip', default='localhost', 
        help='ip address to bind to', metavar='IPADDRESS')
    _paser.add_option('-m', '--module', dest='module', default='pyUwf', 
        help='module to import can be a full path', metavar='MODULE')
    _paser.add_option('-f', '--function', dest='func', default='kick_start',
        help='function to link to  webserver to', metavar='FUNC')
    _paser.add_option('-s', '--script_name', dest='script', default='blog',
        help='function to link to  webserver to', metavar='SCRIPT_NAME')
    _paser.add_option('-t', '--threads', dest="threads", default=1, type='int',
        help= 'Number of background responds threads created.')
    _paser.add_option('-r', '--path_render_engine', dest="pre", default='', 
        help= 'path to template engine')
    _paser.add_option('-n', '--name_render_engine', dest="re", default='', 
        help= 'naem of the template engine to import')

    (options, args) = _paser.parse_args(p_argv)

    return( options, args)

if __name__ == "__main__":
    (options, args)= parse_args(argv[1:])
    ar = importlib.import_module(options.module)
    #_dis = {}
    if hasattr(ar, options.func) : 
        ap = getattr(ar, options.func)
        serve(ap, host=options.ip, port= options.port, threads=options.threads)

    else:
        print('failed to start')

