import psycopg2, psycopg2.extras, psycopg2.errors
import cgi, os, importlib, time
import pyctemplate   #template engine
from urllib.parse import quote_plus, urlparse, urlencode, parse_qs
from zlib import adler32
import globals as g 
from datetime import datetime as dt 
from datetime import timedelta as td

import mimetypes as mt 
import apps.session_controller as session 
session.SEC = g.SEC

##this is the main driving function it runs the below start up functions
# if all are true it then searches for the app to be called then processes it
#      
def kick_start(enviro, start_response):
    try :
        if not check_paths():
            return server_respond(pstatus='500 ', 
                poutput='paths declared in globals.py failed', pre=None,
                sr=start_response)
        else:
            append_to_sys_path()
        if not connect_to_db(pwd='123456'):
            return server_respond(pstatus='500 ', 
                poutput='Can not connect to the Database', pre=None,
                sr=start_response)
        _results, ENVIRO, POST, GET, CSB, APPSTACK, COOKIES, CLIENT_STATE = load_enviro(enviro, ENVIRO=g.ENVIRO, APPSTACK=g.APPSTACK)
        _cs_results, CLIENT_STATE = session.load_session(COOKIES.get('session_id'), APPSTACK=APPSTACK, ENVIRO=ENVIRO, CLIENT_STATE=CLIENT_STATE)
        if not _results :
            error('Load Enviroment return false, can not continue ')
            return server_respond(pstatus='500 ', 
                poutput='load enviro error', pre=None, sr=start_response)
        if not check_SSL(enviro):
            return server_respond(pstatus='500 ', 
                poutput='SSL Check failure', pre=None, sr=start_response)
        if ENVIRO.get('SERVE_STATIC_FILES', False) and APPSTACK is None : 
            _results, _output = get_static_url_file(GET.get('url_path',''), False, ENVIRO=ENVIRO)
            if not _results:
                raise Exception('Could not find the requested URI')
            set_static_file_cache_header(ENVIRO=ENVIRO)
            return server_respondf(pstatus='200 ', 
                pheaders=ENVIRO.get('HEADERS'),
                poutput= _output,
                sr=start_response
                )
        else: 
            if CSB == '':
                CSB = session.load_CSB(POST, GET, session.SEC)
            _test, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB = run_pyapp( 
                    papp_filename=APPSTACK.get('filename',None),
                    papp_path=APPSTACK.get('path', None),
                    papp_command=APPSTACK.get('command',None),
                    ptemplate_stack=APPSTACK.get('template_stack',None),
                    pcontent_type=APPSTACK.get('content_type',None),
                    pserver_cache_on=APPSTACK.get('server_cache_on',False),
                    pserver_cache_age =APPSTACK.get('server_cache_age',0),
                    pcacheability =APPSTACK.get('cacheability', 'no-sotre'),
                    pcache_age=APPSTACK.get('cache_age',0),
                    POST=POST, 
                    GET=GET, 
                    ENVIRO=ENVIRO,
                    CLIENT_STATE=CLIENT_STATE,  
                    COOKIES=COOKIES, 
                    CONTEXT={},
                    CSB=CSB,
                    TEMPLATE='', 
                    TEMPLATE_ENGINE=g.TEMPLATE_ENGINE
                )
            if _test:
                return server_respond(poutput=_output, 
                    pheaders=ENVIRO.get('HEADERS'), 
                    penviro=ENVIRO, 
                    pcookies=COOKIES, 
                    pcsb=CSB,
                    pre=None,
                    sr=start_response)
            else:
                run_pyapp()
    except Exception as _e:
        #catch any exception if the error template is setup return result to the client if not rethrow exception
        _ea = g.APPSTACK.get("error")
        _et = g.TEMPLATE_STACK.get(_ea.get('template_stack'))
        if _ea and _et : 
            _results, _output = error_catcher(_ea, _et, _e, ENVIRO=ENVIRO, TEMPLATE_ENGINE=g.TEMPLATE_ENGINE,
                POST=POST, GET=GET, CLIENT_STATE=CLIENT_STATE, COOKIES=COOKIES, CONTEXT={},
                CSB=CSB, TEMPLATE='')
            return server_respond(pstatus='500',
                pheaders={'Content-type': 'text/html'},
                poutput=_output,
                sr=start_response)
        else: 
            raise Exception("Error Template or App Stack not setup rethrowing the error.") from _e
    return server_respond(pstatus='500 ',
        pcontext=[],
        pheaders={'Content-type': 'text/plain'},
        pre=None,
        poutput='Internal Server Error No Command Sent',
        sr=start_response
        )

def error_catcher(p_AS={}, p_TS=[], pe=Exception(), ENVIRO={}, TEMPLATE_ENGINE=None,
        POST={}, GET={}, CLIENT_STATE={}, COOKIES={}, CONTEXT={},
        CSB='', TEMPLATE=''):
    """
    p_AS is the app stack entry 
    p_TS is the template stack
    pe is the exception class passed into the function 
    Error Catcher takes in the app and template dictionary builds the template then calls the command noted in 
    app stack 
    """
    _com = p_AS.get('command', '')
    _et = ''
    _template_ext= ENVIRO.get('TEMPLATE_EXTENSION','.html')
    
    _is_in_cache, _raw_template, _template_name = build_template('error', p_TS, True, _template_ext, ENVIRO)
    if len(_raw_template)==0:
        raise Exception("The error handler could not build its template") from pe
        
    _er = importlib.import_module(p_AS.get('filename', ''), _com)
    if hasattr(_er, _com) : 
        return getattr( _er, _com)(_raw_template, pe, ENVIRO=ENVIRO, TEMPLATE_ENGINE=TEMPLATE_ENGINE,
            POST=POST, GET=GET, CLIENT_STATE=CLIENT_STATE, COOKIES=COOKIES, CONTEXT={},
            CSB=CSB, TEMPLATE=''
        )
    else:
        raise Exception('The error handler is not setup correctly in the app stak or is missing ') from pe

def get_static_url_file(pfull_path='', pcheck_file_only =False, ENVIRO={}):
    _filepath = convert_url_path_server_path(pfull_path, ENVIRO)
    _found =  os.path.isfile(_filepath)
    _output= b''
    if _found and pcheck_file_only ==False:
        _fp = open(_filepath, 'rb')
        _output =  _fp.read()
        _fp.close()
        _type, _encode = mt.guess_type(_filepath, strict=False)
        if _type is None :
            _type = 'plain/text'
        ENVIRO.get('HEADER',{}).update({'Content-type': _type })
    return _found, _output

def set_static_file_cache_header(pcacheability='public', pmethod='max-age', p_age=0, ENVIRO={}):
    if p_age ==0 and pmethod in ('max-age', 's-maxage', 'stale-while-revalidate', 'stale-if-error' ):
        p_age = ENVIRO.get('STATIC_FILES_CACHE_AGE', 600)
        ENVIRO.get('HEADER',{}).update({'Cache-Control': pcacheability + ' ' + pmethod + '=' + str(p_age)} )
    else:
        ENVIRO.get('HEADER',{}).update({'Cache-Control': pcacheability })

def convert_url_path_server_path(p_upath='', ENVIRO={}):
    
    if len(p_upath)==0:
        return ''
    if p_upath[0:1] in ('/', "\\" ):
        p_upath = p_upath[1:]
    _url_path = p_upath.split('/')
    for key, value in sorted(ENVIRO.items()):
        if not isinstance(value, dict):
            continue 
        _check = value.get('urlpath',None)
        if _check is None:
            continue
        _compare = ''
        _count = 1
        for parts in _url_path:
            _compare = _compare + '/' + parts
            if _compare == _check:
                return value.get('filepath', '') + '/'.join(_url_path[_count:])
            _count +=1
    return ''

#converts the headers, enviroment, to bytes 
# runs the template engine and converts the result to bytes
#calls the start_reponse function passing the status and headers out
# and returns output reponse to be passed back to mod_wsgi
def server_respond(pstatus='200',
        pheaders={},
        penviro={},
        pcookies=session.COOKIES_to_Send,
        pre=None,
        poutput='',
        sr=None,
        CLIENT_STATE={},
        pcsb=''
       ):
    
    session.save_session(CLIENT_STATE, CLIENT_STATE.get('SESSION_ID')) ## save the client state prior to sending sending data
    
    _head = list(pheaders.items()) # wsgi wants this as list 
    if len(pcookies) > 0 :
        cc =[('Set-Cookie', str(v).strip() +";" ) for k, v in pcookies.items()] #put in the cookies 
        aa =[('Set-Cookie', session.COOKIES_to_Send.output(attrs=None, header='', sep=''))]
        _head.extend( aa)
    _outputB = poutput.encode(encoding='utf-8', errors='replace')

    ##add the content length just before returning wsgi module
    _head.append( ('Content-Length', str(len(_outputB))))
    sr(pstatus, _head)
    return [_outputB]

##server responds for returning files and other content that is not Python App
def server_respondf(pstatus='200', 
        pheaders={},
        poutput=None,
        sr = None):
    _head = list(pheaders.items()) # wsgi wants this as list 
    if len(poutput) == 0 :
        poutput ==b'failed to find the file'
        pass
    ##add the content length just before returning wsgi module
    for k, v in _head:
        if not isinstance(k, str):
            bb = 'problem'
        if not isinstance(v, str):
            bb = 'problem'
    if _head is None :
        _head =  ('Content-Length', str(len(poutput)))
    else:
        _head.append(('Content-Length', str(len(poutput))))
    sr(pstatus, _head)
    return [poutput]

def clear_globals():
    g.POST = {}
    g.ERRORSTACK = []
    g.GET = {}
    g.ENVIRO.update({'HEADERS':{}})
    g.COOKIES = g.cookies.BaseCookie()
    g.COOKES_to_Send = g.cookies.BaseCookie()

def run_pyapp(papp_filename='', 
                papp_path='.', 
                papp_command='init', 
                ptemplate_stack='',
                pcontent_type='', 
                pcheck_CSB = True,
                pserver_cache_on=False,
                pserver_cache_age = 0,
                pcacheability = 'no-sotre',
                pcache_age=0,
                POST={}, 
                GET={}, 
                ENVIRO={},
                CLIENT_STATE={},  
                COOKIES={}, 
                CONTEXT={},
                CSB= '',
                TEMPLATE='', 
                TEMPLATE_ENGINE=None
            ):
    """
    papp_filename: is the python module being dynamically imported 
    papp_path: is the path to the module it should follow python . notation
    papp_command: the function in the module that will be executed. 
    ptemplate_stack: template stack that is rendered by the app
    pcontect_type: html content type retuned to the browes 
    pcheck_CSB: this stage check the CSB entry to the one in the server if it does not no other 
    pserver_cache_on :=False is the server allowed to use local cache rendering of previous results
    pserver_cache_age: = in seconds the 
    pcacheability:  allow the client to cache the results 
    pcache_age=0: if the client is allowed to cache how long is it good for 
    processing is done default is to check the CSB.

    the function must return a boolean type.  if this function is called recursively 
    there is logic built in to redirect or call a different app to render a different result. 
    Method ONE is a recursive call must return False to prevent the Output buffer 
        from being re-rendered and just call run_pyapp setting the parameters as nessarcy 
    Method TWO return true set  the  global context  and template_stack varabiles to be rendered
    Method THREE is set the global varabel redirect which is check prior in the server return function, 
        clears the output buffer,  you can use a query string or users_session to do additional procesing

    Keep in mind the CSB entry may have already checked and deleted from the database there may be a need
    to set the pcheck_CSB to false on recurvise run_pyapp to allow additional processing  

    if server side cacheing is used this means one can not relie on CSB no post form should ever use caching. 

    """
    if papp_filename == '':
        error('No App_name passed in Failed', 'run_pyapp')
        return False, ''
    ## lets see if the app is allowed to be cached if so do we have cached version to send to the client?
    _results, _output = results_cache_is_in('post_render_'+papp_filename + "_" + papp_command + ".html", pserver_cache_age, ENVIRO)
    if pserver_cache_on and _results:
        return True, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB      
    
    CONTEXT=add_to_Context(CONTEXT, POST, GET, ENVIRO, CLIENT_STATE, COOKIES,  TEMPLATE, CSB)
    _ar = importlib.import_module(papp_filename, papp_command) 
    _result = False
    
    if hasattr(_ar, papp_command) : 
        if not session.check_credentials(papp_command, CLIENT_STATE): #check secuirty
            _result = session.load_login_page("This function %s requires you to be logged in "%(papp_command) )
        else :
            if len(TEMPLATE)==0: ##
                _template_stack = match_template_to_app(ptemplate_stack, 
                                                    papp_command, 
                                                    papp_filename, 
                                                    g.ENVIRO.get('TEMPALATE_EXTENSION', '.html'))
                _is_in_cache, TEMPLATE, _template_name = build_template(papp_command, _template_stack, True, ENVIRO=ENVIRO)
            #run the cammand being requested  
            _result, _raw_output, ENVIRO, CLIENT_STATE, COOKIES, CSB = getattr(_ar, papp_command)( POST=POST, 
                                                  GET=GET, 
                                                  ENVIRO=ENVIRO,
                                                  CLIENT_STATE=CLIENT_STATE,  
                                                  COOKIES=COOKIES, 
                                                  CONTEXT=CONTEXT, 
                                                  TEMPLATE=TEMPLATE, 
                                                  TEMPLATE_ENGINE=TEMPLATE_ENGINE,
                                                  CSB=CSB

                        ) 
        if _result :
            ENVIRO.get('HEADER',{}).update({'Content-type': pcontent_type })
            if pserver_cache_on:
                results_cache_put_in('post_render_'+papp_filename + "_" + papp_command + ".html", _raw_output, ENVIRO)
        
            return True, _raw_output, ENVIRO, CLIENT_STATE, COOKIES, CSB 
        
        error('Not Critical: recieved a false state from the app ')
        return True, '', ENVIRO, CLIENT_STATE, COOKIES, CSB
    else:
        error('Error could not find  %s command in %s '%(papp_command, papp_filename), '')    

    return False, '',  ENVIRO, CLIENT_STATE, COOKIES, CSB

def match_template_to_app(ptemplate_stack_name, papp_command, papp_filename, p_template_extension='.html'):
    """
    Searches through the TemplateStack using the passed template name if that fails
    it will then use the app_command then the name of the python file where app is stored  
    ptemplate_stack_name :  name of the template stored in the globals.TEMPLATE_STACK
    papp_command : command that is or will be process this is found in the globals.APPSTACK
    papp_filename : name of the py file where the app_command is located.
    """
    ## try to find the template  in the global template_stack dictionary
    #error( 'var pass = %s'% (ptemplate_stack), 'what value is passed into ptemplate_stacks')

    if ptemplate_stack_name in g.TEMPLATE_STACK:
        to_render = g.TEMPLATE_STACK.get(ptemplate_stack_name, None)
        if to_render is None:
            error("failed to render a template for %s" % (ptemplate_stack_name), 'use template stack')
    ## try to use the app name to find the template 
    elif papp_command in g.TEMPLATE_STACK:
        to_render = g.TEMPLATE_STACK.get(papp_command, None)
        if to_render is None: 
            error("failed to render a template for %s" % (papp_filename) , 'use app name')
    ## try to find the template based on the python file itself 
    elif papp_filename in g.TEMPLATE_STACK:
        to_render = g.TEMPLATE_STACK.get(papp_filename, None)
        if to_render is None:
            error("failed to render a template for %s" %(papp_filename), 'use file name')
    else:
        to_render = None
        error("No Template Defined for %s " % ( papp_filename ), 'run_pyapp')
    return to_render

def add_to_Context(CONTEXT={}, 
        POST={}, 
        GET={}, 
        ENVIRO={},
        CLIENT_STATE={},  
        COOKIES={},  
        TEMPLATE='', 
        CSB={}):
    """
    add the enviroment and headers to the globals.CONTEXT.
    this is called prior to CONTEXT being passed into the HTML rendering engin
    """
    #
    CONTEXT.update({'HEADERS': ENVIRO.get('HEADERS', {})})
    CONTEXT.update({'IMAGES':ENVIRO.get('IMAGES','')})
    CONTEXT.update({'DOCS':ENVIRO.get('DOCS','')})
    CONTEXT.update({'STATIC':ENVIRO.get('STATIC','')})
    CONTEXT.update({'MEDIA':ENVIRO.get('MEDIA','')})
    CONTEXT.update({'SITE_NAME':ENVIRO.get('SITE_NAME','NOT SET')})
    CONTEXT.update({'APPURL':ENVIRO['PROTOCOL'] + g.ENVIRO.get('HTTP_HOST')+ '/' + g.ENVIRO.get('SCRIPT_NAME','')} )
    CONTEXT.update({'CSB':CSB})
    CONTEXT.update({'COOKIES':COOKIES})
    CONTEXT.update({'GET':GET})
    CONTEXT.update({'POST':POST})
    return CONTEXT
        
def match_uri_to_app(puri='', APPSTACK={}, ENVIRO={} ):
    """
        pass in the URI and the APPSTACK to search through to find a match returning the APPSTACK Entry 
        first search is a simple match using the entire uri_path to match to the APP_STACK entry
        second search then breaks the URI_PATH into sections breaking at "/" to find a match
        third search then does second serach in reverse. 
        fall back is to go back to the root app defined with / in globals.APPSTACK
        if no root is set then it is set to NONE. 
    """
    #lets do the simple match first
    if puri in APPSTACK :
        return True, APPSTACK.get(puri)
    ##simple match failed now we process the URI starting at the end 
    # trying to find a matching app pulling each part of the path.
    
    for _ic in range(1, puri.count('/')):
        _test = puri[0: puri.find('/', 0, _ic)]
        if _test in APPSTACK:
            return True, APPSTACK.get(_test)
    #failed to match yet again  now just try matching at each part of the uri
    # split apart the URI at "/" and load the rest of the path in not matched  
    # uri global varaible 
    for _parts in reversed(puri.split('/')) :
        if _parts in APPSTACK :
            return True, g.APPSTACK.get(_parts)
    ## exhausted all matches going to the root
    if convert_url_path_server_path(puri, ENVIRO) == "":
        if '/' in APPSTACK:
            return True, APPSTACK.get('/', {})
    return False, None
        
def check_app_in_appstack():
    if g.ENVIRO['PYAPP_TO_RUN'] in g.APPSTACK.keys():
        return True
    return False

def build_template(papp_name='', ptstack=[], p_check_components=True, p_template_extension='.html', ENVIRO={} ):
    """
        papp_name: name of the application  that has been called
        ptstask : template stack to build the tempalte
        p_check_components: compare the components listed in the Template stack 
        to are newer than the built template in the cache   
        Constructs the template to be render from the different files listed in the Template_Stake
        Before building a new template it 
    """
    _error_mess = ''
    _template_name = papp_name + p_template_extension
    _fpath_template=  ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER',os.getcwd()) + _template_name

    if template_cache_is_in(_template_name, ENVIRO ) :
        if p_check_components :
            if template_age_vs_parts_age(_fpath_template, ptstack, ENVIRO):
                return True, template_cache_get(_template_name, 'string', ENVIRO=ENVIRO), _template_name
        else:
            return True, template_cache_get(_template_name, 'string', ENVIRO=ENVIRO), _template_name
    ## YES NOT pythonic but need to know if on first item in the list
    ## and can not pop it as it would alter the global stack during run time 
    ## we do not want to do that...  
    _bts = ''
    _path = ENVIRO.get('TEMPLATE_PATH', '')
    for  _i in  ptstack: 
        _fp = _path+_i 
        _rstring = '<TEMPLATE name="%s"/>' % (_i)
        if os.path.isfile(_fp):
            _tp = open(_fp, 'r')
            _tp.seek(0)
            if _bts.find(_rstring) == -1:
                if _bts.find('</body>') == -1:
                    _bts += _tp.read()
                else :
                     _bts = _bts.replace(_rstring, _tp.read() + '</body>' )
            else :
                _bts = _bts.replace(_rstring, _tp.read())
        else:
            error('Failed to find the template %s for app %s' %(_i, papp_name), 'build template')
    return (template_cache_put_in(_template_name , _bts, ENVIRO), _bts, _template_name)

def get_template_stack(pkey):
    g.TEMPLATE_STACK.get(pkey, [])

def template_age_vs_parts_age(p_rendered_template='', ptstack={}, ENVIRO={} ):
    """ Compares the age of an allready rendered template to the component parts of the template 
    if component parts of the template are newer than the rendered template return False.  
    """
    _date = os.path.getctime(p_rendered_template)
    _path = ENVIRO.get('TEMPLATE_PATH', '')
    for _cts in ptstack:
        if _date < os.path.getctime(_path +_cts):
            return False
    return True

def template_cache_is_in(pkey_value, ENVIRO ): #returns true if the cached file is found and set global template_to_render 
    ##todo is refactor the render engine to work on file like objects instead of paths
    ## this allow storing  pickled objects in memcache and use of spooled in memory temp files 
    _path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER','')
    if ENVIRO.get('MEMCACHE_USE', False):
        cached_file = MEMCACHE.get(pkey_value)
        if cached_file is None:
            return False
        tfile = open(_path+pkey_value, 'w+b')
        tfile.write(cached_file)
        tfile.close() 
        
        return True    
    elif os.path.isfile(_path+pkey_value):
        fpath =  _path + pkey_value 
        age = dt.fromtimestamp(os.path.getmtime(fpath)) + td(seconds=ENVIRO.get('TEMPLATE_CACHE_AGING_SECONDS', 30))
        if dt.now() > age :
            os.remove(fpath)
            return False
        return True
    return False
    
def template_cache_put_in(key_value, content, ENVIRO ):
    if ENVIRO.get('MEMCACHE_USE', False):
        MEMCACHE.set(key_value, content) ##this will need more work to probably have to use pickle
    path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', '')
    cfile = open(path+key_value, 'w')
    cfile.write(content)
    cfile.close()
    return True

def template_cache_get(pkey_value, preturn_type='string', pmode='r', ENVIRO={}, ):
    """
        pkey_value : id key of the template in the cache
        return_type :  string returns the file contents; fpn returns the full path to the file, fo returns the file object 
        return_type is ignored if cache type is anything other than file
        pmode: mode the file is opened in only used when fo is passed in  
        get the pre-rendered-template out of the cache  
    """
    if ENVIRO.get('MEMCACHE_USE', False):
        return MEMCACHE.get(pkey_value)
    
    path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', '')
    if preturn_type=='fpn':
        return path 
    elif preturn_type=='string':
        cfile = open(path+pkey_value, 'r')
        return cfile.read()
    elif preturn_type== 'fo':
        return   open(path+pkey_value, pmode)

    return None

def results_cache_put_in(key_value, content, ENVIRO={}):
    """ this holds the results for previous runs of an app. 
    """
    if ENVIRO.get('MEMCACHE_USE', False):
        g.MEMCACHE.set(key_value, content) ##this will need more work to probably have to use pickle
    path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER','')
    cfile = open(path+key_value, 'w', encoding='utf-8')
    cfile.write(content)
    cfile.close()
    return True

def results_cache_is_in(pkey_value, p_age, ENVIRO={}): 
    """returns true if the cached file is found  and the age is less than p_age
    """
    _path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER','')
    if ENVIRO.get('MEMCACHE_USE', False):
        if pkey_value not in g.MEMCACHE:
            return False, ''
        return True , g.MEMCACHE.get(pkey_value)
    elif os.path.isfile(_path+pkey_value):
        fpath =  _path + pkey_value 
        age = dt.fromtimestamp(os.path.getmtime(fpath)) + td(seconds=p_age)
        if dt.now() > age :
            os.remove(fpath)
            return False, ''
        _f = open(fpath, encoding='utf-8') 
        return True, _f.read()
    return False, ''

def load_enviro(e, ENVIRO={}, POST={}, GET={}, CSB='', APPSTACK={}, CLIENT_STATE={} ): ##scan through the enviroment object setting up our global objects convert from bytes
    ENVIRO.update({'SERVER_NAME': bytes_to_text(e.get('SERVER_NAME'))})
    ENVIRO.update({'SERVER_PORT': bytes_to_text(e.get('SERVER_PORT'))})
    ENVIRO.update({'HTTP_ACCEPT_LANGUAGE': bytes_to_text(e.get('HTTP_ACCEPT_LANGUAGE'))})
    ENVIRO.update({'REQUEST_SCHEME': bytes_to_text(e.get('REQUEST_SCHEME'))})
    ENVIRO.update({'HTTP_USER_AGENT': bytes_to_text(e.get('HTTP_USER_AGENT'))})
    ENVIRO.update({'REMOTE_ADDR': bytes_to_text(e.get('REMOTE_ADDR'))})
    if 'mod_wsgi.script_name' in e:
        ENVIRO.update({'SCRIPT_NAME':bytes_to_text(e.get('mod_wsgi.script_name'))})
    else:
        ENVIRO.update({'SCRIPT_NAME':bytes_to_text(e.get('SCRIPT_NAME'))})
    if 'mod_wsgi.path_info' in e:
        ENVIRO.update({'URI_PATH':bytes_to_text(e.get('mod_wsgi.path_info'))})
    elif 'PATH_INFO' in e:
        ENVIRO.update({'URI_PATH': bytes_to_text(e.get('PATH_INFO'))})
    if len(ENVIRO.get('URI_PATH',''))<1:
        ENVIRO.update({'URI_PATH':bytes_to_text(e.get('REQUEST_URI'))})

    if not change_base_url( bytes_to_text(e.get('HTTP_HOST', '') )
                        , bytes_to_text(e.get('SERVER_PORT') )):
        return False,ENVIRO, POST, GET, CSB, APPSTACK

    ENVIRO.update({'PROTOCOL': identify_protocol(e.get('SERVER_PROTOCOL','http://'))})

    ENVIRO['STATIC']['furlpath']= build_url_root_path() + g.ENVIRO['STATIC']['urlpath']
    ENVIRO['IMAGES']['furlpath']= build_url_root_path() + g.ENVIRO['IMAGES']['urlpath']
    ENVIRO['DOCS']['furlpath']= build_url_root_path() + g.ENVIRO['DOCS']['urlpath']
    ENVIRO['MEDIA']['furlpath']=build_url_root_path() + g.ENVIRO['MEDIA']['urlpath']
    
    CLIENT_STATE = g.CLIENT_STATE
    #Load Parse and Process the POST and GET commands
    
    if e.get('REQUEST_METHOD').upper() == 'POST':
        _result, POST, CSB = parse_POST(e)
        _result, APPSTACK = match_uri_to_app(ENVIRO.get('URI_PATH'), APPSTACK, ENVIRO)
        _result, COOKIES = session.load_cookies(e.get('HTTP_COOKIE'))
    elif e.get('REQUEST_METHOD').upper() == 'GET':
        _result, GET, CSB =parse_GET(e)
        _result, APPSTACK = match_uri_to_app(ENVIRO.get('URI_PATH'), APPSTACK, ENVIRO) # find the python applicaiton to run 
        _result, COOKIES =session.load_cookies(e.get('HTTP_COOKIE')) # load the cookies sent and may load a save session state 
    
    return _result, ENVIRO, POST, GET, CSB, APPSTACK, COOKIES, CLIENT_STATE

def parse_POST(web_enviro, POST={}, CSB=''):
    script = ( web_enviro.get('REQUEST_URI', '').encode('iso-8859-1').decode(errors='replace') or
            web_enviro.get('SCRIPT_NAME', '').encode('iso-8859-1').decode(errors='replace') or 
            web_enviro.get('REDIRECT_URL', '').encode('iso-8859-1').decode(errors='replace')
        )
    POST.update({'url_path': script})
    POST.update({'POST_COUNT':0})
    try:
        request_body_size = int(web_enviro.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    if request_body_size > 0:
        form_data = parse_qs(web_enviro.get('wsgi.input').read(request_body_size))
        for key, value in form_data.items():
            POST.update({bytes_to_text(key): [bytes_to_text(i) for i in value]})
            POST['POST_COUNT']+= 1
        CSB = POST.get('CSB', [''])[0]
    POST.update({'CONTENT_TYPE': web_enviro.get('CONTENT_TYPE')})
    return True, POST, CSB

def parse_GET(web_enviro, GET={}, CSB=''):
    _url = bytes_to_text(web_enviro.get('REQUEST_URI', b''))
    GET.update({"PATH_TO_APP":bytes_to_text(web_enviro.get('mod_wsgi.path_info','')) })
    GET.update({'SCRIPT_ROOT':bytes_to_text(web_enviro.get('mod_wsgi.script_name',''))})
    if _url is None:
        return True
    else :
        script = ( _url.encode('iso-8859-1').decode(errors='replace') or 
                    _url.encode('iso-8859-1').decode(errors='replace')
                )      
    GET.update({'url_path': script})
    qs = web_enviro.get('QUERY_STRING', '')
    GET.update({'QUERY_STRING_COUNT':0})
    if isinstance(qs, bytes): ##url encoded data typically ascii
        try:
            qs = parse_qs(qs.decode(g.ENVIRO.get('ENCODING', 'utf-8')))
        except UnicodeDecodeError:
            # ... but some user agents are misbehaving :-(
            qs = parse_qs(qs.decode('iso-8859-1'))
    else:
        qs=parse_qs(qs)
    if len(qs) > 0:
        for key, value in qs.items():
            GET.update({
                bytes_to_text(key) :
                [bytes_to_text(i) for i in value]
            })
            GET['QUERY_STRING_COUNT']+=1
        CSB = GET.get('CSB', [''])[0]
    return True, GET, CSB

def sanitize_input(p_input):
    pass

def sanitize_html(p_input):
    pass
    
def bytes_to_text(_p, encode=g.ENVIRO.get('ENCODING', 'utf-8')):
    if isinstance(_p, bytes):
       return str(_p, encode, 'replace')
    return _p

def connect_to_db(host='127.0.0.1', 
                    db='blog', 
                    user='justin', 
                    pwd='', 
                    port=5432, 
                    driver='Postgresql',
                    named_for_connection='' ):
    
    if len(named_for_connection) == 0:
        conname = 'PG' + str(len(g.CONN)+1)
    else:
        conname = named_for_connection
    if driver == 'Postgresql':       
        g.CONN.update({ conname :
                psycopg2.connect( host=host, dbname=db, user=user, 
                password=pwd, port=port )
            })
    return True    

def get_db_connection(connection_name = 'PG1'): #either the index or named connection
    return g.CONN.get(connection_name)

def run_sql_command(p_sql, p_topass= None):
    _con = g.CONN.get('PG1',None)
    if _con is None:
        return {}
    _cur = _con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) 
    try :
        _cur.execute(p_sql, p_topass)
    except psycopg2.ProgrammingError as e :
        import traceback as tb 
        _stack = tb.print_stack()
        _db_error = [ x for x in e.args]
        _error_mess = """SQL ERROR the last command sent ' %(command)s
        caused the following error %(error)s 
        parameters= %(parameters)s
        Exception Call Stack """ % {'command':p_sql, 'error':_db_error, 'parameters':str(p_topass)}   
        _con.rollback()
        raise Exception(_error_mess) from e 
    except Exception as e:  #yes this is a generic catch but there are hundreds of different possible execptions declared in pyscopg2 class 
        import traceback as tb 
        _stack = tb.print_stack()
        _last_command = _cur.query.decode('utf-8')
        _db_error = [ x for x in e.args]
        _error_mess = """SQL ERROR the last command sent ' %(command)s
        caused the following error %(error)s 
        Exception Call Stack """ % {'command':_last_command, 'error':_db_error}   
        _con.rollback()
        raise Exception(_error_mess) from e 
    try:
        _return = _cur.fetchall()
        _con.commit()
        return _return
    except psycopg2.ProgrammingError : ##this is annoying can not call any fetches with zero results as it throws this exception 
       return {'state': _con.commit() }

def create_template_engine():
    # test to see if the template has been create if not
    # import the default engine and put it in here
    if g.TEMPLATE_ENGINE:
        #from pyctemplate import compile_template  #template engine
        from python_html_parser import render_html
        g.TEMP_ENGINE=render_html
    return True

def get_template_engine():
    return g.TEMP_ENGINE

def check_SSL(e):
    if session.SEC['SSL_REQUIRE']:
        if e.get('HTTPS', 'off') in ('on', '1'):
            return client_redirect('/ssl_requried', 
                '307 Temporary Redirect', b'')       
    return True

def log_event(mess, level='DEBUG'):
    import logging
    return True

def error(pmessage =' not set ', psource='unkown', 
            plog='ERROR', 
            preturn_to_client=g.ENVIRO['ERROR_RETURN_CLIENT']):
    if g.ENVIRO['LOG_LEVEL'] == 'DEBUG': #log everything
        g.ERRORSTACK.append([
            (" Source: %s" % (psource)),
            (" Message: %s" % (pmessage))
         ])
        return True
    elif (plog == 'WARNING'  or plog == 'ERROR') \
            and g.ENVIRO['LOG_LEVEL'] == 'WARNING':
        g.ERRORSTACK.append([
            (" Source: %s"% (psource)),
            (" Message: %s" % (pmessage))
         ])
        return True
    elif plog == 'ERROR' \
            and g.ENVIRO['LOG_LEVEL'] == 'ERROR':
        g.ERRORSTACK.append([
            (" Source: %s"% (psource)),
            (" Message: %s"% (pmessage))
         ])
        return True
    return True

def build_template_key(pdic={}, pout='file.ctemplates', ptype='file', html_start= '', html_end= '', html_start_loob = '', html_end_loop='' ):
    """
    pdic: dictionary to iterate over creating the template tags
    pout: is the file name to writ out to
    ptype: default file or string writes out to a file or returns a string parsed dictoinary
    """
    _r = ''
    if isinstance(pdic, dict):
        _r = break_apart_dic(pdic, '', html_start, html_end, html_start_loob, html_end_loop)
    
        if ptype == 'file':
            if os.path.exists(pout) :
                return 
            _f = open(pout,'w')
            _f.write(_r)
        elif ptype == 'string':
            return _r
    return ''

def break_apart_dic(pdic={}, p_prefix='', html_start= '', html_end= '', html_start_loob = '', html_end_loop=''):
    _output = ''
    if len(p_prefix) >0 :
        _op = p_prefix + '.'
    else:
        _op = ''
    if isinstance(pdic, dict):
        for key, value in sorted(pdic.items()):
            if isinstance(value, list):
                _output = _output + break_apart_dic(value, key, html_start, html_end, html_start_loob, html_end_loop )
            elif p_prefix >'' and isinstance(value,dict):
               
                _output = _output + break_apart_dic(value, _op + key, html_start, html_end, html_start_loob, html_end_loop)
            elif isinstance(value, dict):
                _output = _output +  break_apart_dic(value, key, html_start, html_end, html_start_loob, html_end_loop )
            else:
                _output =  '%s %s <TMPL_VAR name="%s%s"> %s %s' % (_output, html_start ,_op ,key, html_end, chr(10), )
    elif isinstance(pdic, list):
        _output = '%s<TMPL_LOOP name="%s"> %s %s' % (html_start_loob, p_prefix, chr(10), chr(9)) 
        for i in pdic:
            if isinstance(i, dict):
                _output = _output + break_apart_dic(i, '', html_start, html_end, html_start_loob, html_end_loop )
        _output =  '%s</TMPL_LOOP> %s %s' %(_output, html_end_loop, chr(10) )
    return _output 

def build_html_template(phtml_header={}, pinclude_templates={},  pdic={} ):
    pass

def build_url_root_path():
    """builds the current root URL path http(s)://server(:port)/
    returns string"""
    _path = g.ENVIRO.get('PROTOCOL') + g.ENVIRO.get('HTTP_HOST')
    if  str(g.ENVIRO.get('SERVER_PORT', 80)) != '80':
        _path += ':'+ g.ENVIRO.get('SERVER_PORT')
    return _path 

def build_url_links(p_descrip_command={}, p_url_path=None, 
                p_app_command=None, p_protocol=None, p_host=None, p_port=None):
    
    """creates url(s) from dictionary
    p_descrip_command is dictionary looking for key values  containing the 
            Name: for URL to be reference in the template, 
            LinkText: of the URL and the 
            URL also can be a GET command the ?id=1&view_state=1234..etc
            NOTE any slashed in the URL dictionary converted quoted safe ;
    p_url_path: default will use the current url path the app is using or can be passed in
    p_app_command: default will use the current app being processed by the application stack  
    p_host: default is the passed in host name from webserver enviroment
    p_port: default is the passed in port from the webserver enviroment
    returns: a disction  
    """
    if len(p_descrip_command) ==0:
        return None
    if p_protocol is None:
        p_protocol = g.ENVIRO.get('PROTOCOL')
    if p_port is None:
        if str(p_port) == '80' and  str(g.ENVIRO.get('SERVER_PORT')) == '80':
            p_port =  ''
        else :
            p_port = ':%s'%g.ENVIRO.get('SERVER_PORT')
    else:
        p_port = ':%s'%p_port
    if p_host is None:
        p_host = g.ENVIRO.get('HTTP_HOST')  
    if p_url_path is None:
        p_url_path =  g.ENVIRO.get('URI_PATH') +'/'
    if p_app_command is None:
        p_app_command = ''
    else :
        p_app_command += p_app_command + '/'
    r_urls = {}
    for bl in p_descrip_command :
        _link = p_protocol+p_host + p_port + p_url_path + p_app_command, quote_plus(bl['url'])
        _url_string = """<a href="%s">%s</a>""" %(_link, bl['linktext'])
        r_urls.update( {bl['name']:_url_string})

    return r_urls 

def get_db_next_id(p_sequence_name='', p_con=None ):
    if p_con is None:
        p_con = get_db_connection()
    q_str = """ select nextval(%(p_sequence_name)s) as key_id """
    cur = p_con.cursor()
    cur.execute(q_str, {'p_sequence_name':p_sequence_name} )
    _rec = cur.fetchall()
    if len(_rec) ==0:
        return -1
    return _rec[0][0]

def test_for_entries_in(p_list=[], p_dict={}):
    """ takes a list of strings then test if the values 
        are keys in the dictionary then returns a list of 
        entries missing
    """
    _return = []
    for _i in p_list:
        if _i not in p_dict:
            _return.append(_i)
    return _return 

def create_access_list_from_py(p_pythonFile='', p_con=None):
    if p_pythonFile == '' and p_con is None:
        return False
    import inspect as ins
    ar = importlib.import_module(p_pythonFile)
    _list = ins.getmembers(ar)

    q_str = """insert into sec_access  
            ( sa_allowed, sa_target_id, sa_target_type,
            sa_app_name, sa_app_function)
               values (  
                %(sa_allowed)s ,
                %(sa_target_id)s ,
                %(sa_target_type)s,
                %(sa_app_name)s ,
                %(sa_app_function)s 
            )
            on conflict do nothing;
        """
    cur = p_con.cursor()

    for _i in _list:
        if ins.isfunction(_i[1]):
            cur.execute(q_str,
            { 
               'sa_allowed': True,
               'sa_target_id': 1,
               'sa_target_type': 'user',
               'sa_app_name': p_pythonFile,
               'sa_app_function': _i[0]
                }
            )
    return 

def add_to_security(p_id, p_sec_type, p_app_name, p_app_function, p_allowed=False ):
    pass

def create_access_list_from_app( p_app_stack={}, p_con=None):
    if p_app_stack == '' and p_con is None:
        return False
    
    q_str = """insert into sec_access  
            ( sa_allowed, sa_target_id, sa_target_type,
            sa_app_name, sa_app_function)
               values (  
                %(sa_allowed)s ,
                %(sa_target_id)s ,
                %(sa_target_type)s,
                %(sa_app_name)s ,
                %(sa_app_function)s 
            )
            on conflict do nothing;
        """
    cur = p_con.cursor()
    for _key, _value in sorted(p_app_stack.items()):
        cur.execute(q_str,
            { 
            'sa_allowed': not _value['security'],
            'sa_target_id': 1,
            'sa_target_type': 'user',
            'sa_app_name': _key,
            'sa_app_function': _value['command']
            }
        )
    return 

def create_default_users_grp(p_con):
    if p_con is None:
        p_con = get_db_connection()

    q_str = """
        insert into users ( 
                user_id,
                user_name ,
                user_last,
                user_email ,
                user_type ,
                user_pwd ,
                user_grp )
            values
            ( 0, 'admin', '', 'admin@local', 'user',
             crypt('123456'::text, gen_salt('md5')), 0),
            ( 1, 'public', 'general access', 'public@local', 'user',
             '', 0);
        insert into sec_groups (
            sg_id ,
            sg_name ,
            sg_descrip,
            sg_members
        ) values
        (0, 'administrators','super user groups', '{0}'),
        (1, 'everyone','unauthentiaed users', '{0,1}');
    """
    cur = p_con.cursor()
    cur.execute(q_str)
    p_con.commit()

def check_paths():
    """goes over the file paths defined in the globals file 
    making sure they exists
    """
    try :
        if not os.path.exists(g.ENVIRO.get('TEMPLATE_PATH')):
            os.makedirs(g.ENVIRO.get('TEMPLATE_PATH'), 0o755)
            
        if not os.path.exists(g.ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER')):
            os.makedirs(g.ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER'), 0o755)
        
        if not os.path.exists(g.ENVIRO.get('TEMPLATE_CACHE_PATH_POST_RENDER')):
            os.makedirs(g.ENVIRO.get('TEMPLATE_CACHE_PATH_POST_RENDER'), 0o755)

        if not os.path.exists(g.ENVIRO.get('MEDIA').get('filepath')):
            os.makedirs(g.ENVIRO.get('MEDIA').get('filepath'), 0o755)
        
        if not os.path.exists(g.ENVIRO.get('STATIC').get('filepath')):
            os.makedirs(g.ENVIRO.get('STATIC').get('filepath'), 0o755)
        
        if not os.path.exists(g.ENVIRO.get('IMAGES').get('filepath')):
            os.makedirs(g.ENVIRO.get('IMAGES').get('filepath'), 0o755)
        
        for _p in g.APPS_PATH:
            if not os.path.exists(_p):
                os.makedirs(_p, 0o755)
    except OSError as e:
        error(str(e), 'check_paths_function')
        return False

    return True

def append_to_sys_path():
    from sys import path
    for _p in g.APPS_PATH:
        path.append(_p)

def change_base_url(pchange_to='', pport=80):
    
    #does the host protocol contain the port number some webservers have the port number in the http_host_name 
    have_port =pchange_to.find(':')
    if have_port>0:
        pchange_to = pchange_to[0:have_port] 
    if pchange_to not in g.ALLOWED_HOST_NAMES :
        error('Can Not change BASE URL not list in the allowed host')
        return False
    if pchange_to is not None:
        if pport == 80:
            g.ENVIRO.update({'HTTP_HOST': pchange_to} )
            return True
        else:
            g.ENVIRO.update({'HTTP_HOST': pchange_to})
            g.ENVIRO.update({'SERVER_PORT' : str(pport)})
            return True
    return False

def identify_protocol (p_protocol):
    if  p_protocol == 'HTTP/1.1':
        return 'http://'
    elif  p_protocol == 'HTTP':
        return 'http://'
    elif  p_protocol == 'HTTPS':
        return 'https://' 
    dd = ''
    dd.find(':')

def add_to_APPSTACK(app_function_name, 
            template_stack,
            filename, 
            path,
            command , 
            security=False,
            content_type='text/html',
            server_cache_on=True,
            server_cache_age=30,
            cacheability='private',
            cache_age=30):
    """ todo need to at data sanity checks all these values before adding them to the appstack 
    """

    g.APPSTACK.update({app_function_name:
        {'template_stack':template_stack,
         'filename': filename, 
         'path':path,
         'command':command , 
         'security':security ,
         'content_type':content_type,
         'server_cache_on':server_cache_on,
         'server_cache_age':server_cache_age,
         'cacheability':cacheability,
         'cache_age':cache_age}
        }
        )

def get_APPSTACK():
    return g.APPSTACK

def add_to_TEMPLATE_STACK():
    pass

def check_dict_for_list(pdict={}):
    _return={}
    for k, v in sorted(pdict.items()): 
        if isinstance(v, list):
            _return.update({k:convert_list_to_list_of_dict(v, k)})
        else:
            _return.update({k:v})
    return _return 

def convert_list_to_list_of_dict(plist=[], key_value='converted.' ):
    _return_list_dict=[]
    _count = 1
    for il in plist:
        if isinstance(il,dict):
            _return_dict.append({key_value:check_dict_for_list(pdict)})
        elif isinstance(il,list):
            return_dict.append(
                    {key_value+ str(_count):
                    convert_list_to_list_of_dict(il, key_value + ".list")
                    }
                )
        else:
            _return_list_dict.append({key_value+str(_count):il})
        _count = _count + 1
    return _return_list_dict
#print(break_apart_dic(g.APPSTACK, '' ))
 