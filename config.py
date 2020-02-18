from datetime import datetime, timedelta

#config file is where all the globals of the app are created
#you can add to any of the globals here in latter code just adds to it
# the post and get dictionaries are not cleared 


APPSTACK={} ## disctionary of python files and commands to return html file
CONN = None ## connections to database servers
SEC = {} ## user and password and parts of the website  a user is allowed to
TEMP_ENGINE = None  ##create the temp engine once then access it here
ENVIRO = {} ##global server enviroment
HEADERS ={} ##header recorders also contains the cookies
OUTPUT = '' ##BUFFER in string its converted to bytes just prior to be sent back to mod_wsgi
POST = {} ##POST command comming from webserver 
GET = {} ## get commands comming from the server
TEMPLATE_STACK = {} ##setups template Stack, a dictionary of list. This means you can have 
#basic HTML page with headers css and dev tags, Setup is App/script file then a list of
# files that get added together to build a page. example is such
# {'index.py', ['main_page.pyhtml, search_bar.pyhtml', results.pyhtml] }
# this get processed in order appended to the end of each other, or looks for tag
# <$TEMPLATE$ NAME OF TEMPLATE $TEMPLATE$> to insert the template
# with all templates context varable must contain all objects and variables 
# needed to process the template. 
# EXTREME CARE must be taken that when chaining templates that variables are not overwritten
# and the driving scripts are called and results placed into the context varable prior to 
# calling render engine which is suppose to happen just prior returning results
# to the web_client.  Template engine can be called out of order and the results placed
# in the output buffer.
TEMPLATE_ENGINE = {}
TEMPLATE_TO_RENDER = {} ##the current template that is to be rendered
CONTEXT = {} #location where to stick objects and variables that are latter passed 
# into the rendering engine. this is Dictionary of list where the keys match the html tags    
MEMCACHE = {} ## in memory cache templates, files, images, query results  
STATUS = {} ##HTML STATUS  when setting manually do not for get a space after then number
ERRORSTACK  = {} ## stack of none fatal errors/warrings that have been created
ERRORSSHOW = False
##seconds in the future until a cookie expires  

CSB = '' ##cross script block uuid must be added to all the forms and is checked during load enviro, 
            ## is save in user enviroment. it is reset after every request so single use only. 
HTTP_REDIRECT = '' # variable to hold the url to redirect the client to.  
# If it is NOT NONE it will send the redirect to the client 

HTTP_REDIRECT = None

base_directory = '/home/MAGWERKS.COM/justin/github/pyUweb/'
#base_directory = '/home/justin/git_hub/pyUweb/'



def SEC():
    return {
    'REQUIRE_LOGGIN':False,
    'SSL_REQUIRE':False,
    'USER_LOGGEDIN':False,
    'USER_AUTOLOGIN':True,
    'USER_ID': -1,
    'USER_NAME':'',
    'USER_EMAIL':'',
    'USER_PWD':'',
    'USER_IPADDRESS':'',
    'USER_CLIENT':'0.0.0.0',
    'USER_ACCESS':[{'app_name_function':True,}],
    'USER_GROUP':[{'group_name': True}],
    'USER_TIMER':60000,
}
def get_cs():
    return {
        'last_command':'',
        'prev_state':'',
        'USER_ID':'',
        'TIMEOUT':datetime.utcnow() + timedelta(seconds=60000),
        'session_id':'',
        }
def get_enviro():
    return {
    'DOCS':{'urlpath':'/documents', 'filepath':base_directory+'static/documents/', 'furlpath':''},
    'LOG_LEVEL': 'DEBUG',
    'ENCODING':'utf-8',
    'ERROR_RETURN_CLIENT':True,
    'ERROR_LOG':'system',
    'MEDIA':{'urlpath':'/media', 'filepath':base_directory+'static/media/', 'furlpath':''},
    'MEMCACHE_USE':False, 
    'APP_NAME':'/', #default to root this is the app name for the app_stack dictionary 
    'PROTOCOL':'http',
    'SITE_NAME':'Magwerks Service Website',
    'SCRIPT_NAME':'',
    'URI_PATH': '',
    'SERVER_NAME':'',
    'SERVER_PORT':'',
    'HTTP_HOST':'', 
    'SERVE_STATIC_FILES': True,
    'STATIC_FILES_CACHE_AGE':600, ## Cache Age of static files the system assumes public storage allowed this can be overriden 
    'STATIC':{'urlpath':'/static', 'filepath':base_directory+'static/', 'furlpath':''},
    'IMAGES':{'urlpath':'/static/images', 'filepath':base_directory+'static/images/', 'furlpath':''},
    'TEMPLATE_PATH':base_directory+'templates/',
    'TEMPLATE_CACHE_PATH_PRE_RENDER':base_directory+'cache/pre_render/',
    'TEMPLATE_CACHE_PATH_POST_RENDER':base_directory+'cache/post_render/', # location where the file are stored before being passed through template_engine
    'TEMPLATE_CACHE_AGING_SECONDS':300,
    'TEMPLATE_TYPE': 'file',  #ctemplate works off a string containing the html sent to it or path/filename to the html template 
    'TEMPALATE_EXTENSION':'.html',
    'STATUS':'200',
    'URL_CURRENT_PATH':'',
    'HEADERS':{
        'Content-Type':'text/html;',
        'charset':'UTF-8',
        },
    'ALLOWED_HOST_NAMES': ['localhost', '127.0.0.1', 'g-server', '192.168.1.72', '192.168.1.120'],
    'APPS_PATH':(base_directory+'apps',),
    'USING_WAITRESS':True,
    'CAPTICHA_client_key': '6LcMYdQUAAAAAPn2Z6HFBKoVPNApIyhe5stGMQWZ',
    'CAPTICHA_server_key': '6LcMYdQUAAAAAK-3eKpSJXsU0s4Zwq8VEITzmas2',
    }

ERRORSTACK =[]
ERRORSSHOW = True



"""
if ENVIRO['MEMCACHE_USE']:
    from pymemcache.client import mem
    MEMCACHE = mem.Client(('localhost', 11211))
"""

def get_te(path=''):
    import sys
    sys.path.append('/home/MAGWERKS.COM/justin/github/ptython_HTE/')
    #_loca = importlib.util.spec_from_file_location('python_html_parser', '../ptyhon_HTE/')
    import python_html_parser  #default template engine

    return python_html_parser.render_html  #map the function to this global 
TEMPLATE_TO_RENDER = '' ##


CONN={}


def CLIENT_STATE():
    return {
        'last_command':'',
        'prev_state':'',
        'USER_ID':'',
        'TIMEOUT':datetime.utcnow() + timedelta(seconds=SEC['USER_TIMER']),
        'session_id':'',
        }

## the template extension is 


#list of comon content types 
CONTENT_TYPES = {
    'application':[
        "application/EDI-X12",  
        "application/EDIFACT",  
        "application/javascript",   
        "application/octet-stream",   
        "application/ogg",   
        "application/pdf", 
        "application/xhtml+xml",   
        "application/x-shockwave-flash",    
        "application/json",  
        "application/ld+json",  
        "application/xml",   
        "application/zip",  
        "application/x-www-form-urlencoded", 
    ],
    'audio':[
        'audio/mpeg',   
        'audio/x-ms-wma',   
        'audio/vnd.rn-realaudio',   
        'audio/x-wav',
    ],
    'multipart':[
        'multipart/mixed',    
        'multipart/alternative',   
        'multipart/related (using by MHTML (HTML mail).)',  
        'multipart/form-data',     
    ],
    'text':[
        'text/css',    
        'text/csv',    
        'text/html',    
        'text/javascript (obsolete)',
        'text/plain',    
        'text/xml',
    ],
    'video':[
        'video/mpeg',
        'video/mp4',
        'video/quicktime',
        'video/x-ms-wmv',
        'video/x-msvideo',
        'video/x-flv',
        'video/webm',
    ]   
}