import wsgiserver, importlib
from optparse import OptionParser as op
from sys import argv



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
    (options, args) = _paser.parse_args(p_argv)

    return( options, args)

def Dispachters():
    return 


if __name__ == "__main__":
    (options, args)= parse_args(argv[1:])

    ar = importlib.import_module(options.module)

    if hasattr(ar, options.func) : 
        ap = getattr(ar, options.func)
        _d = wsgiserver.WSGIPathInfoDispatcher({'/'+ options.script: ap})
        server = wsgiserver.WSGIServer(_d, host=options.ip, port=options.port)
        server.start()
    else:
        print('failed to start')

