import psycopg2, psycopg2.extras, psycopg2.errors
import cgi, os, importlib, time
import pyctemplate   #template engine
from urllib.parse import quote_plus, urlparse, urlencode, parse_qs
from zlib import adler32
import globals as g 
from datetime import datetime as dt 
from datetime import timedelta as td

import mimetypes as mt 
import uuid
import apps.session_controller as session 

##this is the main driving function it runs the below start up functions
# if all are true it then searches for the app to be called then processes it
#      
def kick_start(enviro, start_response):
    try :
        clear_globals()
        if not check_paths():
            return server_respond(pstatus='500 ', 
                poutput='paths declared in globals.py failsed', pre=None,
                sr=start_response)
        else:
            append_to_sys_path()
        if not connect_to_db(pwd='123456'):
            return server_respond(pstatus='500 ', 
                poutput='Can not connect to the Database', pre=None,
                sr=start_response)
        elif not load_enviro(enviro):
            error('Load Enviroment return false, can not continue ')
            return server_respond(pstatus='500 ', 
                poutput='load enviro error', pre=None, sr=start_response)
        elif not check_SSL(enviro):
            return server_respond(pstatus='500 ', 
                poutput='SSL Check failure', pre=None, sr=start_response)
        elif g.ENVIRO['PYAPP_TO_RUN'] is None:
            ## load enviroment should have put app to run here if it is none match failed so must be returning a static file 
            if g.SERVE_STATIC_FILES : 
                if get_static_url_file(g.GET.get('url_path','')):
                    set_static_file_cache_header()
                    return server_respondf(pstatus='200 ', 
                            pheaders=g.HEADERS,
                            poutput= g.OUTPUT,
                            sr=start_response
                            )
            return server_respond(pstatus='500 ', 
                poutput='URI did not match to anything on this server', pre=None,
                sr=start_response)
        else:
            _ap=  g.ENVIRO['PYAPP_TO_RUN']
            _test = run_pyapp( 
                    papp_filename= _ap.get('filename',None),
                    papp_path=     _ap.get('path', None),
                    papp_command=   _ap.get('command',None),
                    ptemplate_stack=_ap.get('template_stack',None),
                    pcontent_type=  _ap.get('content_type',None),
                    pserver_cache_on = _ap.get('server_cache_on',False),
                    pserver_cache_age = _ap.get('server_cache_age',0),
                    pcacheability = _ap.get('cacheability', 'no-sotre'),
                    pcache_age = _ap.get('cache_age',0)
                )
            if _test:
                return server_respond(poutput=g.OUTPUT,
                    pre=None,
                    sr=start_response)
            else:
                run_pyapp()
    except Exception e:
        #catch any exception if the error template is setup return result to the client if not rethrow exception
        _ea = g.APPSTACK.get("error")
        _et = g.TEMPLATE_STACK.get(_ea.get('template_stack'))
        if _ea and _et : 
            _output = error_catcher(_ea, _et, e )
            return server_respond(pstatus='500',
                pheaders={'Content-type': 'text/plain'}
                poutput=_output,
                sr=start_response)
        else: 
            raise e
    return server_respond(pstatus='500 ',
        pcontext=[],
        pheaders={'Content-type': 'text/plain'},
        pre=None,
        poutput='Internal Server Error No Command Sent',
        sr=start_response
        )

def error_catcher(p_AS={}, p_TS=[]):
    """
    p_AS is the app stack entry 
    Error Catcher is the function called to redirect sys.stderr so it can be formated and sent back client interface
    it recieves an app stack to find the py  file looks for the command entry and template to use to.
    it links the command entry to the sys.stderror
    """
    _com = p_AS.get('command', '')
    _et = ''
    if build_template('error', p_TS, False, False):
        _et = template_cache_get('error'+g.TEMPALATE_EXTENSION)
    else:
        raise Exception('The error handler could not build it template')
    _er = importlib.import_module(p_AS.get('filename', ''), _com)
    if hasattr(_er, _com) : 
        sys.stdout = getattr(_er, _com)
        sys.stderr = getattr(_er, _com)
    else:
        raise Exception('The error handler is not setup correctly in the app stak or is missing ')

def get_static_url_file(pfull_path='', pcheck_file_only =False):
    _filepath = convert_url_path_server_path(pfull_path)
    _found =  os.path.isfile(_filepath)
    if _found and pcheck_file_only ==False:
        _fp = open(_filepath, 'rb')
        g.OUTPUT = _fp.read()
        _fp.close()
        _type, _encode = mt.guess_type(_filepath, strict=False)
        if _type is None :
            _type = 'plain/text'
        g.HEADERS = {'Content-type': _type}
    return _found

def set_static_file_cache_header(pcacheability='public', pmethod='max-age', p_age=0 ):
    if p_age ==0 and pmethod in ('max-age', 's-maxage', 'stale-while-revalidate', 'stale-if-error' ):
        p_age = g.ENVIRO.get('STATIC_FILES_CACHE_AGE', 600)
        g.HEADERS.update({'Cache-Control': pcacheability + ' ' + pmethod + '=' + str(p_age) } )
    else:
        g.HEADERS.update({'Cache-Control': pcacheability })

def convert_url_path_server_path(p_upath=''):
    
    if len(p_upath)==0:
        return ''
    if p_upath[0:1] in ('/', "\\" ):
        p_upath = p_upath[1:]
    _url_path = p_upath.split('/')
    for key, value in sorted(g.ENVIRO.items()):
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
def server_respond(pstatus=g.STATUS,
        pcontext=g.CONTEXT,
        pheaders=g.HEADERS,
        penviro=g.ENVIRO,
        pcookies=g.COOKES_to_Send,
        pre=None,
        poutput='',
        sr=None):
    
    session.save_session(g.CLIENT_STATE, g.CLIENT_STATE.get('SESSION_ID')) ## save the client state prior to sending sending data
    if g.HTTP_REDIRECT is not None:  ## something has set the global Redirect varaible clear output
        client_redirect(url=g.HTTP_REIRECT)  ## this was most likely already called eariler but we will call it again to make sure the headers are set
        poutput = '' #
        
    _head = list(pheaders.items()) # wsgi wants this as list 
    if len(g.COOKES_to_Send) > 0 :
        cc =[('Set-Cookie', str(v).strip() +";" ) for k, v in pcookies.items()] #put in the cookies 
        aa =[('Set-Cookie', g.COOKES_to_Send.output(attrs=None, header='', sep=''))]
        _head.extend( aa)
    _outputB = poutput.encode(encoding='utf-8', errors='replace')

    ##add the content length just before returning wsgi module
    _head.append( ('Content-Length', str(len(_outputB))))
    sr(pstatus, _head)
    return [_outputB]

##server responds for returning files and other content that is not Python App
def server_respondf(pstatus=g.STATUS, 
        pheaders=g.HEADERS,
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
    g.HEADERS = {}
    g.OUTPUT = ''
    g.CONTEXT = {}
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
                pcache_age=0):
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

    if server side cacheing is used this means one can not relie on CSB 

    """
    if papp_filename == '':
        error('No App_name passed in Failed', 'run_pyapp')
        return False
    ## lets see if the app is allowed to be cached if so do we have cached version to send to the client?
    if pserver_cache_on and \
        results_cache_is_in('post_render_'+papp_filename + "_" + papp_command + ".html", pserver_cache_age, True):
        return True      
    #lets check the CSB key in the saved session if valid continue with the 
    #saved session from the database.  if not die 
    if not check_CSB(g.CSB):
        error('CSB has expired or is not present should redirect to root or login page the CSB created aknew')
    
    add_globals_to_Context()
    _ar = importlib.import_module(papp_filename, papp_command) 
    _result = False
    _to_render = False
    if hasattr(_ar, papp_command) : 
        if not session.check_credentials(papp_command): #check secuirty
            _result = session.load_login_page("This function %s requires you to be logged in "%(papp_command) )
            _to_render = True 
        else :
            _to_render = match_template_to_app(ptemplate_stack, papp_command, papp_filename)
            _result = getattr(_ar, papp_command)() #run the cammand being requested  
        if _to_render and _result :
            try :
                g.CONTEXT.update({'CSB':save_CSB(g.SEC['USER_ID'])})
                g.OUTPUT= g.TEMPLATE_ENGINE(g.TEMPLATE_TO_RENDER, 
                            g.CONTEXT, 
                            g.ENVIRO.get('TEMPLATE_TYPE'), 
                            g.ENVIRO.get('TEMPLATE_TMP_PATH'))
                if pserver_cache_on :
                    result_cache_put_in('post_render_'+papp_filename + "_" + papp_command  + ".html", g.OUTPUT)

                g.HEADERS['Content-Type']= pcontent_type
                return True
            except AttributeError as e :
                error("""Failed to render Template %s 
                        Render Engine Error %s
                        typically the context structure is wrong %s""" %
                        (g.TEMPLATE_TO_RENDER, 
                        str(e),
                        str(g.CONTEXT) 
                        )
                    )
                return False
        else:
            error('Not Critical: ran the app but did not have template to process ')
        return True
    else:
        error('Error could not find  %s command in %s '%(papp_command, papp_filename), '')    

    return False

def match_template_to_app(ptemplate_stack, papp_command, papp_filename):
    """
    Searches through the TemplateStack using the passed template name if that fails
    it will then use the app_command then the name of the python file where app is stored  
    ptemplate_stack :  name of the template stored in the globals.TEMPLATE_STACK
    papp_command : command that is or will be process this is found in the globals.APPSTACK
    papp_filename : name of the py file where the app_command is located.
    """
    ## try to find the template  in the global template_stack dictionary
    #error( 'var pass = %s'% (ptemplate_stack), 'what value is passed into ptemplate_stacks')
    if ptemplate_stack in g.TEMPLATE_STACK:
        to_render = build_template( papp_command, 
                    g.TEMPLATE_STACK[ptemplate_stack])
        if not to_render:
            error("failed to render a template for %s" % (ptemplate_stack), 'use template stack')
    ## try to use the app name to find the template 
    elif papp_command in g.TEMPLATE_STACK:
        error('entered template via app_command', 'run_pyapp')
        to_render = build_template( papp_filename, 
                    g.TEMPLATE_STACK[papp_command])
        if not to_render: 
            error("failed to render a template for %s" % (papp_filename) , 'use app name')
    ## try to find the template based on the python file itself 
    elif papp_filename in g.TEMPLATE_STACK:
        error('entered template via filename', 'run_pyapp')
        to_render = build_template( papp_filename, 
                    g.TEMPLATE_STACK[papp_filename])
        if not to_render:
            error("failed to render a template for %s" %(papp_filename), 'use file name')
    else:
        to_render = False
        error("No Template Defined for %s " % ( papp_filename ), 'run_pyapp')
    return to_render

def add_globals_to_Context():
    """
    add the enviroment and headers to the globals.CONTEXT.
    this is called prior to CONTEXT being passed into the HTML rendering engin
    """
    #
    g.CONTEXT.update({'HEADERS': g.HEADERS})
    g.CONTEXT.update({'IMAGES':g.ENVIRO.get('IMAGES','')})
    g.CONTEXT.update({'DOCS':g.ENVIRO.get('DOCS','')})
    g.CONTEXT.update({'STATIC':g.ENVIRO.get('STATIC','')})
    g.CONTEXT.update({'MEDIA':g.ENVIRO.get('MEDIA','')})
    g.CONTEXT.update({'SITE_NAME':g.ENVIRO.get('SITE_NAME','NOT SET')})
    g.CONTEXT.update({'APPURL':g.ENVIRO['PROTOCOL'] + g.ENVIRO.get('HTTP_HOST')+ '/' + g.ENVIRO.get('SCRIPT_NAME','')} )
    g.CONTEXT.update({'SEC':g.SEC})
    g.CONTEXT.update({'CSB':g.CSB})
    g.CONTEXT.update({'COOKIES':g.COOKIES})
    return True
        
def match_uri_to_app():
    """
        uses the global.ENVIRO[URI_PATH] variable searches through globals.APPSTACK
        locking for possible match , then copies the APPSTACK entry into the globals.ENVIRO[PYAPP_TO_RUN],
        if no match is found it is set to NONE 
        first search is a simple match using the entire uri_path to match to the APP_STACK entry
        second search then breaks the URI_PATH into sections breaking at "/" to find a match
        third search then does second serach in reverse. 
        fall back is to go back to the root app defined with / in globals.APPSTACK
        if no root is set then it is set to NONE. 
    """
    #lets do the simple match first
    if g.ENVIRO['URI_PATH'] in g.APPSTACK :
        g.ENVIRO['PYAPP_TO_RUN'] = g.APPSTACK[g.ENVIRO['URI_PATH']]
        return True
    ##simple match failed now we process the URI starting at the end 
    # trying to find a matching app pulling each part of the path.
    _uri = g.ENVIRO['URI_PATH']
    for _ic in range(1, _uri.count('/')):
        _test = _uri[0: _uri.find('/', 0, _ic)]
        if _test in g.APPSTACK:
            g.ENVIRO['PYAPP_TO_RUN'] = g.APPSTACK[_test]
            g.ENVIRO['URI_PATH_NOT_MATCHED']= _uri[len(_test):]
            return True 
    #failed to match yet again  now just try matching at each part of the uri
    # split apart the URI at "/" and load the rest of the path in not matched  
    # uri global varaible 
    _notused = ''
    _return = False
    for _parts in reversed(_uri.split('/')) :
        if _parts in g.APPSTACK :
            g.ENVIRO['PYAPP_TO_RUN'] = g.APPSTACK[_parts]
            g.ENVIRO['URI_PATH_NOT_MATCHED']= _notused
            return True
        else:
            _notused = _parts + '/' + _notused
    ## exhausted all matches going to the root
    if '/' in g.APPSTACK and (len(g.ENVIRO['URI_PATH'])>0 and g.SERVE_STATIC_FILES==False) :
        g.ENVIRO['PYAPP_TO_RUN'] = g.APPSTACK['/']
        return True
    else :   
        g.ENVIRO['PYAPP_TO_RUN'] = None ##all has failed to set the pyapp to run to None 
    ## no root command has been setup 
    g.ENVIRO['URI_PATH_NOT_MATCHED']= g.ENVIRO['URI_PATH']
    return False

def check_app_in_appstack():
    if g.ENVIRO['PYAPP_TO_RUN'] in g.APPSTACK.keys():
        return True
    return False

def build_template(papp_name='', ptstack=[], pupdate_global=True, p_check_components=True ):
    """
        papp_name: name of the application  that has been called
        ptstask : template stack to build the tempalte
        pupdate_global: update the globals.TEMPLATE_TO_RENDER 
        p_check_components: compare the components listed in the Template stack 
        to are newer than the built template in the cache   
        Constructs the template to be render from the different files listed in the Template_Stake
        Before building a new template it 
    """
    _error_mess = ''
    _template_name = papp_name + g.TEMPALATE_EXTENSION
    _fpath_template=  g.ENVIRO.get('TEMPLATE_CACHE_PATH',os.getcwd()) + _template_name
    if pupdate_global:
        g.TEMPLATE_TO_RENDER =_fpath_template
    if template_cache_is_in(_template_name, pupdate_global) :
        if p_check_components :
            if not template_age_vs_parts_age(_fpath_template, ptstack):
                return True
    ## YES NOT pythonic but need to know if on first item in the list
    ## and can not pop it as it would alter the global stack during run time 
    ## we do not want to do that...  
    _bts = ''
    _path = g.ENVIRO.get('TEMPLATE_PATH', '')
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
    return template_cache_put_in(papp_name + g.TEMPALATE_EXTENSION , _bts)

def template_age_vs_parts_age(p_rendered_template='', ptstack={} ):
    """ Compares the age of an allready rendered template to the component parts of the template 
    if component parts of the template are newer than the rendered template return False.  
    """
    _date = os.path.getctime(p_rendered_template)
    _path = g.ENVIRO.get('TEMPLATE_PATH', '')
    for _cts in ptstack:
        if _date < os.path.getctime(_path +_cts):
            return False
    return True

def template_cache_is_in(pkey_value, set_global=True): #returns true if the cached file is found and set global template_to_render 
    ##todo is refactor the render engine to work on file like objects instead of paths
    ## this allow storing  pickled objects in memcache and use of spooled in memory temp files 
    _path = g.ENVIRO.get('TEMPLATE_CACHE_PATH','')
    if g.ENVIRO.get('MEMCACHE_USE', False):
        cached_file = g.MEMCACHE.get(pkey_value)
        if cached_file is None:
            return False
        tfile = open(_path+pkey_value, 'w+b')
        tfile.write(cached_file)
        tfile.close() 
        if not set_global:
            return True
        g.TEMPLATE_TO_RENDER = _path + pkey_value 
        return True    
    elif os.path.isfile(_path+pkey_value):
        fpath =  _path + pkey_value 
        age = dt.fromtimestamp(os.path.getmtime(fpath)) + td(seconds=g.ENVIRO.get('TEMPLATE_CACHE_AGING_SECONDS', 30))
        if dt.now() > age :
            os.remove(fpath)
            return False
        if not set_global:
            return True
        g.TEMPLATE_TO_RENDER = _path + pkey_value
        return True
    return False
    
def template_cache_put_in(key_value, content ):
    if g.ENVIRO.get('MEMCACHE_USE', False):
        g.MEMCACHE.set(key_value, content) ##this will need more work to probably have to use pickle
    path = g.ENVIRO.get('TEMPLATE_CACHE_PATH', '')
    cfile = open(path+key_value, 'w')
    cfile.write(content)
    cfile.close()
    return True

def template_cache_get(pkey_value, preturn_type='string', pmode='r'):
    """
        pkey_value : id key of the template in the cache
        return_type :  string returns the file contents; fpn returns the full path to the file, fo returns the file object 
        return_type is ignored if cache type is anything other than file
        pmode: mode the file is opened in only used when fo is passed in  
        get the template out of the cache and 
    """
    if g.ENVIRO.get('MEMCACHE_USE', False):
        return g.MEMCACHE.get(key_value)
    
    path = g.ENVIRO.get('TEMPLATE_CACHE_PATH', '')
    if preturn_type=='fpn':
        return path 
    elif preturn_type=='string':
        cfile = open(path+key_value, 'r')
        return cfile.read()
    elif preturn_type== 'fo':
        return   open(path+key_value, pmode)

    return None

def result_cache_put_in(key_value, content):
    """ this holds the results for previous runs of an app. 
    """
    if g.ENVIRO.get('MEMCACHE_USE', False):
        g.MEMCACHE.set(key_value, content) ##this will need more work to probably have to use pickle
    path = g.ENVIRO.get('TEMPLATE_TMP_PATH','')
    cfile = open(path+key_value, 'w', encoding='utf-8')
    cfile.write(content)
    cfile.close()
    return True

def results_cache_is_in(pkey_value, p_age, p_put_into_buffer): 
    """returns true if the cached file is found  and the age is less than p_age
    if the p_put_into_buffer reads the file into the buffer
    """
    _path = g.ENVIRO.get('TEMPLATE_TMP_PATH','')
    if g.ENVIRO.get('MEMCACHE_USE', False):
        if pkey_value not in g.MEMCACHE:
            return False
        if p_put_into_buffer:
            g.OUTPUT = g.MEMCACHE.get(pkey_value)
        return True 
    elif os.path.isfile(_path+pkey_value):
        fpath =  _path + pkey_value 
        age = dt.fromtimestamp(os.path.getmtime(fpath)) + td(seconds=p_age)
        if dt.now() > age :
            os.remove(fpath)
            return False
        if p_put_into_buffer:
            _f = open(fpath, encoding='utf-8')
            g.OUTPUT = _f.read()
        return True
    return False

def put_query_result_in():
    return None

def load_enviro(e): ##scan through the enviroment object setting up our global objects convert from bytes
    g.APACHE_ENVIRO=e ##keep copy in the globals for grins & giggles
    g.ENVIRO['SERVER_NAME']= bytes_to_text(e.get('SERVER_NAME'))
    g.ENVIRO['SERVER_PORT']= bytes_to_text(e.get('SERVER_PORT'))
    g.ENVIRO['HTTP_ACCEPT_LANGUAGE']= bytes_to_text(e.get('HTTP_ACCEPT_LANGUAGE'))
    g.ENVIRO['REQUEST_SCHEME'] = bytes_to_text(e.get('REQUEST_SCHEME'))
    g.ENVIRO['HTTP_USER_AGENT'] = bytes_to_text(e.get('HTTP_USER_AGENT'))
    g.ENVIRO['REMOTE_ADDR'] = bytes_to_text(e.get('REMOTE_ADDR'))
    if 'mod_wsgi.script_name' in e:
        g.ENVIRO['SCRIPT_NAME'] =bytes_to_text(e.get('mod_wsgi.script_name'))
    else:
        g.ENVIRO['SCRIPT_NAME'] =bytes_to_text(e.get('SCRIPT_NAME'))
    if 'mod_wsgi.path_info' in e:
        g.ENVIRO['URI_PATH'] = bytes_to_text(e.get('mod_wsgi.path_info'))
    elif 'PATH_INFO' in e:
        g.ENVIRO['URI_PATH'] = bytes_to_text(e.get('PATH_INFO'))
    if len(g.ENVIRO['URI_PATH'])<1:
        g.ENVIRO['URI_PATH'] = bytes_to_text(e.get('REQUEST_URI'))

    if not change_base_url( bytes_to_text(e.get('HTTP_HOST', '') )
                        , bytes_to_text(e.get('SERVER_PORT') )):
        return False

    g.ENVIRO.update({'PROTOCOL': identify_protocol(e.get('SERVER_PROTOCOL','http://'))})

    g.ENVIRO['STATIC']['furlpath']= build_url_root_path() + g.ENVIRO['STATIC']['urlpath']
    g.ENVIRO['IMAGES']['furlpath']= build_url_root_path() + g.ENVIRO['IMAGES']['urlpath']
    g.ENVIRO['DOCS']['furlpath']= build_url_root_path() + g.ENVIRO['DOCS']['urlpath']
    g.ENVIRO['MEDIA']['furlpath']=build_url_root_path() + g.ENVIRO['MEDIA']['urlpath']
    
    #Load Parse and Process the POST and GET commands

    if e.get('REQUEST_METHOD').upper() == 'POST':
        return parse_POST(e, True)
    elif e.get('REQUEST_METHOD').upper() == 'GET':
        return parse_GET(e,True)
    return False

def parse_POST(web_enviro, update_globals=True):
    script = ( web_enviro.get('REQUEST_URI', '').encode('iso-8859-1').decode(errors='replace') or
            web_enviro.get('SCRIPT_NAME', '').encode('iso-8859-1').decode(errors='replace') or 
            web_enviro.get('REDIRECT_URL', '').encode('iso-8859-1').decode(errors='replace')
        )
    g.POST.update({'url_path': script})
    g.POST.update({'POST_COUNT':0})
    try:
        request_body_size = int(web_enviro.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    if request_body_size > 0:
        form_data = parse_qs(web_enviro.get('wsgi.input').read(request_body_size))
        for key, value in form_data.items():
            g.POST.update({bytes_to_text(key): [bytes_to_text(i) for i in value]})
            g.POST['POST_COUNT']+= 1
        g.CSB = g.POST.get('CSB', [0])[0]
    g.POST.update({'CONTENT_TYPE': web_enviro.get('CONTENT_TYPE')})
    match_uri_to_app() # find the python applicaiton to run 
    load_cookies(web_enviro)  # load the cookies sent and may load a save session state 
    return True

def parse_GET(web_enviro, update_globals=True):
    _url = bytes_to_text(web_enviro.get('REQUEST_URI', b''))
    g.GET.update({"PATH_TO_APP":bytes_to_text(web_enviro.get('mod_wsgi.path_info','')) })
    g.GET.update({'SCRIPT_ROOT':bytes_to_text(web_enviro.get('mod_wsgi.script_name',''))})
    if _url is None:
        return True
    else :
        script = ( _url.encode('iso-8859-1').decode(errors='replace') or 
                    _url.encode('iso-8859-1').decode(errors='replace')
                )      
    g.GET.update({'url_path': script})
    qs = web_enviro.get('QUERY_STRING', '')
    g.GET.update({'QUERY_STRING_COUNT':0})
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
            g.GET.update({
                bytes_to_text(key) :
                [bytes_to_text(i) for i in value]
            })
            g.GET['QUERY_STRING_COUNT']+=1
        g.CSB = g.POST.get('CSB', [0])[0]
    match_uri_to_app() # find the python applicaiton to run 
    load_cookies(web_enviro) # load the cookies sent and may load a save session state 
    return True

def sanitize_input(p_input):
    pass

def sanitize_html(p_input):
    pass

def load_cookies(e):
    _co = session.load_cookies(e.get('HTTP_COOKIE'))
    if _co:
        if _co.get('session_id'): ##see if the session id is set and if we have previous get/post event to process
            for k, v in _co.items():
                g.COOKIES.update({k:v})
            ## load the session from the database if successful skip over  loading the GET and POST enviroments
            if session.load_session(_co.get('session_id')): 
                return True
    else : ##have no session established 
        return session.create_session() 

def check_CSB(pcsb):
    """ antime check_CSB called the database
    copy is purged from database regardless 
    if it is valid or expired 
    """ 
    q_str =""" select true from csb
	            where csb_id = %(pcsb)s 
                and csb_expires > now()"""
    _con = g.CONN.get('PG1')
    _cur =_con.cursor()
    _cur.execute(q_str,{'pcsb':pcsb})
    _r = _cur.fetchall()
    if len(_r) > 0:
        _return = True
        g.CSB_STATUS=True
    else:
        _return = False
        g.CSB_STATUS=False
    q_str = """ delete from csb where csb_id = %(pcsb)s """
    _cur.execute(q_str,{'pcsb':pcsb})
    _con.commit()
    return _return 

def save_CSB(puser_id):
    q_str =""" insert into csb values ( %(session_id)s, 
                now() + interval '30 minutes' )"""
    _con = g.CONN.get('PG1')
    _cur = _con.cursor()
    g.CSB = uuid.uuid1().hex
    _cur.execute(q_str,{'session_id':str(puser_id)+ g.CSB})
    _con.commit()
    return g.CSB

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
    except Exception as e:  #yes this is a generic catch but there around hundred different possible execptions declared in pyscopg2 class 
        import traceback as tb 
        _stack = tb.print_stack()
        _last_command = cur.query.decode('utf-8')
        _db_error = [ x for x in e.args]
        _error_mess = """SQL ERROR the last command sent ' %(command)s
        caused the following error %(error)s 
        Exception Call Stack %(stack)s""" % {'command':_last_command, 'error':_db_error, 'stacks':_stack}   
        error(_error_mess,'pyUwf.py:run_sql_command') 
        _con.rollback()
        return _return 
    try:
        _return = _cur.fetchall()
        _con.commit()
        return _return
    except psycopg2.ProgrammingError : ##this is annoying can not call any fetches with zero results as it throws this error message
       return {'state': _con.commit() }

def create_template_engine():
    # test to see if the template has been create if not
    # import the default engine and put it in here
    if g.TEMPLATE_ENGINE:
        from pyctemplate import compile_template  #template engine
        g.TEMP_ENGINE=compile_template
    return True

def get_template_engine():
    return g.TEMP_ENGINE

def check_SSL(e):
    if g.SEC['SSL_REQUIRE']:
        if e.get('HTTPS', 'off') in ('on', '1'):
            return client_redirect('/ssl_requried', 
                '307 Temporary Redirect', b'')       
    return True

def client_redirect(url=None, redirect_code='307', outputbuffer='', context={}, template={}): # sets the globals up 
    #for a redirect returns false as the kick_start needs to see false to 
    # return to wsgi out of sequence
    g.OUTPUT = outputbuffer
    g.CONTEXT=context 
    if url is not None:
        g.HEADERS['status'] = redirect_code + 'Location:' + url 
        g.HTTP_REDIRECT = url
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
                _output + break_apart_dic(i, p_prefix, html_start, html_end, html_start_loob, html_end_loop )
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
        if not os.path.exists(g.ENVIRO.get('TEMPLATE_TMP_PATH')):
            os.makedirs(g.ENVIRO.get('TEMPLATE_TMP_PATH', 0o755))

        if not os.path.exists(g.ENVIRO.get('TEMPLATE_PATH')):
            os.makedirs(g.ENVIRO.get('TEMPLATE_PATH'), 0o755)
            
        if not os.path.exists(g.ENVIRO.get('TEMPLATE_CACHE_PATH')):
            os.makedirs(g.ENVIRO.get('TEMPLATE_CACHE_PATH'), 0o755)

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

def add_to_TEMPLATE_STACK():
    pass

#print(break_apart_dic(g.APPSTACK, '' ))
