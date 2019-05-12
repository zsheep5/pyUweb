
#config file is where all the globals of the app are created
#you can add to any of the globals here in latter code just adds to it
# the post and get dictionaries are not cleared 


global APPSTACK ## disctionary of python files and commands to return html file
global CONN ## connections to database servers
global SEC ## user and password and parts of the website  a user is allowed to
global TEMP_ENGINE ##create the temp engine once then access it here
global ENVIRO ##global server enviroment
global HEADERS ##header recorders also contains the cookies
global OUTPUT ##BUFFER in string its converted to bytes just prior to be sent back to mod_wsgi
global POST ##POST command comming from webserver 
global GET ## get commands comming from the server
global TEMPLATE_STACK ##setups template Stack, a dictionary of list. This means you can have 
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
global TEMPLATE_ENGINE
global TEMPLATE_TO_RENDER ##the current template that is to be rendered
global CONTEXT #location where to stick objects and variables that are latter passed 
# into the rendering engine. this is Dictionary of list where the keys match the html tags    
global MEMCACHE ## in memory cache templates, files, images, query results  
global STATUS ##HTML STATUS  when setting manually do not for get a space after then number
global ERRORSTACK ## stack of none fatal errors/warrings that have been created
global ERRORSSHOW
global CLIENT_STATE
global COOKIES
global COOKIES_EXPIRES ##number in the future until a cookie expires  
global APPS_PATH  ## list of directories to append to the python sys path to find source files

APPS_PATH = ['/home/justin/git_hub/pyUweb/apps']

APACHE_ENVIRO= None
ENVIRO={
    'DOCS':{'urlpath':'/documents', 'filepath':'/home/justin/git_hub/pyUweb/static/documents', 'furlpath':''},
    'LOG_LEVEL': 'DEBUG',
    'ENCODING':'utf-8',
    'ERROR_RETURN_CLIENT':True,
    'ERROR_LOG':'system',
    'MEDIA':{'urlpath':'/media', 'filepath':'/home/justin/git_hub/pyUweb/static/media', 'furlpath':''},
    'MEMCACHE_USE':False, 
    'PYAPP_TO_RUN':'',
    'PROTOCOL':'http',
    'SITE_NAME':'zSheep Blog',
    'SCRIPT_NAME':'',
    'URI_PATH': '',
    'URI_PATH_NOT_MATCHED':'',
    'SERVER_NAME':'',
    'SERVER_PORT':'',
    'STATIC':{'urlpath':'/static', 'filepath':'/home/justin/git_hub/pyUweb/static/', 'furlpath':''},
    'IMAGES':{'urlpath':'/static/images', 'filepath':'/home/justin/git_hub/pyUweb/static/', 'furlpath':''},
    'TEMPLATE_PATH':'/home/justin/git_hub/pyUweb/templates/',
    'TEMPLATE_CACHE_PATH':'/home/justin/git_hub/pyUweb/cache/pre_render/',
    'TEMPLATE_CACHE_AGING_SECONDS':30,
    'URL_CURRENT_PATH':'',
    'URL':'192.168.1.72',
}
ERRORSTACK =[]
ERRORSSHOW = True



if ENVIRO['MEMCACHE_USE']:
    from pymemcache.client import mem
    MEMCACHE = mem.Client(('localhost', 11211))


from pyctemplate import compile_template  #default template engine

TEMPLATE_ENGINE = compile_template  #map the function to this global 
TEMPLATE_TO_RENDER = '' ##
TEMPLATE_TMP_PATH = '/home/justin/git_hub/pyUweb/cache/post_render/' # staging folder for templates to be written to 
TEMPLATE_TYPE = 'file'  #ctemplate works off a string containing the html sent to it or path/filename to the html template 

HEADERS={
    'Content-Type':'text/plain;',
    'charset':'UTF-8',
}

COOKIES={}
COOKIES_EXPIRES=30

GET={}
POST={}
CONTEXT={}

CONN={}
SEC={
    'REQUIRE_LOGGIN':False,
    'SSL_REQUIRE':False,
    'USER_LOGGEDIN':False,
    'USER_AUTOLOGIN':True,
    'USER_ID': '',
    'USER_NAME':'',
    'USER_EMAIL':'',
    'USER_PWD':'',
    'USER_IPADDRESS':'',
    'USER_CLIENT':'',
    'USER_ACCESS':[{'app_name_function':True,}],
    'USER_GROUP':[{'group_name': True}],
    'USER_TIMER':600,
}
from datetime import datetime, timedelta
CLIENT_STATE = {
    'last_command':'',
    'USER_ID':'',
    'TIMEOUT':datetime.utcnow() + timedelta(seconds=SEC['USER_TIMER'])
    }

##mapping app name and app function to physical/relative path 
# on the server and if login is require
# idea here is the be able to have the code outside apache path 
# { App_name the url post/get: 
#   { filename: "python_file":, 
#     path: 'path to the file'  
#     command:"function to call in python file" 
#     security: bool,
#     content_type: typicaly text/html  this is used by the http client know the type data that was sent 
#   }
# }
# idea is to be similar to django urls function without the complexity 
# after the enviroment is setup match_url_to_app is run 

APPSTACK = {
    '/':{ 'template_stack':'view',
            'filename':'blog', 
            'path':'.',
            'command':'view' , 
            'security':False,
            'content_type': 'text/html',
            },
    'view':{'template_stack':"view", 
            'filename':'blog', 
            'path':'.', 
            'command':'view',
            'security':False,
            'content_type':'text/html',
            },
    'search_blog':{
            'template_stack':'list', 
            'filename':'blog', 
            'path':'.', 
            'command':'search',
            'security':False,
            'content_type': 'text/html',
            },
    'edit_blog':{'filename':'blog', 
              'template_stack':'blog_editor',
              'path':'.',
              'command':'edit_blog', 
              'security':False,
              'content_type': 'text/html',
              },
    'new_blog':{'filename':'blog', 
              'template_stack':'blog_editor',
              'path':'.',
              'command':'new_blog', 
              'security':False,
              'content_type': 'text/html',
              },
    'save_blog':{'filename':'blog', 
              'template_stack':'view',
              'path':'.',
              'command':'save_blog', 
              'security':False,
              'content_type': 'text/html',
              },
    'blog_comment':{'template_stack':'view',
                    'filename':'blog_comment', 
                    'path':'.',
                    'command':'init', 
                    'security':True,
                    'content_type': 'text/html',
                    },
    'create_account':{'template_stack':'view', 
                      'filename':'ca', 
                      'path':'.', 
                      'command':'init', 
                      'security':False,
                      'content_type': 'text/html',
                    },
    'log_in':{'template_stack':'log_in',
             'filename':'', 
             'path':'.', 
             'command':'init', 
             'security':False,
             'content_type': 'text/html',
             },
    'admin':{'template_stack':'view',
             'filename':'admin', 
             'path':'.', 
             'command':'init', 
             'security':True,
             'content_type': 'text/html',
             },
    'image_view':{'template_stack':'view',
                  'filename':'image_view', 
                  'path':'.', 
                  'command':'init', 
                  'security':False,
                  'content_type': 'text/html',
                  },
}
#Template stack layout 
# { App_Nane / URL path relative website root
#   [ list of html files that make up template.  ]
# }
# files must be in the template_path you can do subdirs but no relative imports
# The idea here is you can include many templates to create big template prior
# to being sent to the render engine.  Ctemplate also have include function
# but the results are thrown away after every call.  building the templates this
# allows for caching the result template.  
# If templates do not use <$TEMPLATE$filename.html$TEMPLATE$>
# flag the proceeding templates are appended at the end in order they show in the list.  
TEMPLATE_STACK={
    '/':['main.html', 
            'blog.html', 
            'blog_comments.html', 
            'search.html'],

    'view':['view_page.html',
            'base.html',
            'top_nav_bar.html',
            'side_bar.html',
            'comments.html',
        ],
    'list':['list_page.html',
            'base.html',
            'top_nav_bar.html',
        ],
    'blog_editor':['edit_blog.html',
            'base.html',
            'top_nav_bar.html',
            'js.html',
        ],
    'log_in':['login_html',
            'base.html',
            'top_nav_bar.html',
            'js.html'
        ],
    'error':['error.html'],
}
## the template extension is 
TEMPALATE_EXTENSION = '.html'
STATUS='200 '
OUTPUT = ''

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