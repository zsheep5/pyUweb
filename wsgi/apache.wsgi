
## sample code how to create a apache wsgi file.
## tipically found in the apache webserver path
import posixpath
import sys
sys.path.append('/var/www/blog/wsgi') 
import pyUwf
def _application(environ, start_response):
   return pyUwf.kick_start(environ, start_response)

def application(environ, start_response):
    # Wrapper to set SCRIPT_NAME to actual mount point.
    environ['SCRIPT_NAME'] = posixpath.dirname(environ['SCRIPT_NAME'])
    if environ['SCRIPT_NAME'] == '/':
        environ['SCRIPT_NAME'] = ''
    return _application(environ, start_response)
