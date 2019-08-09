import psycopg2, psycopg2.extras
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
    elif not match_uri_to_app():
        ## failed to match to an app lets see if this request is an file that we can serve out
        if g.SERVE_STATIC_FILES : 
            if get_static_url_file(g.GET.get('url_path')):
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
                papp_filename= _ap['filename'],
                papp_path=     _ap['path'],
                papp_command=   _ap['command'],
                ptemplate_stack=_ap['template_stack'],
                pcontent_type=  _ap['content_type']
            )
        if _test:
            return server_respond(poutput=g.OUTPUT,
                pre=None,
                sr=start_response)
    
    return server_respond(pstatus='500 ',
        pcontext=[],
        pheaders={'Content-type': 'text/plain'},
        pre=None,
        poutput='Internal Server Error No Command Sent',
        sr=start_response
        )

def get_static_url_file(p_full_path=''):
    _filepath = convert_url_path_server_path(p_full_path)
    if os.path.isfile(_filepath):
        _fp = open(_filepath, 'rb')
        g.OUTPUT = _fp.read()
        _fp.close()
        _type, _encode = mt.guess_type(_filepath)
        g.HEADERS = {'Content-type': _type}
        return True
    return False

def convert_url_path_server_path(p_upath=''):
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
        pcookies=g.COOKIES,
        pre=None,
        poutput='',
        sr=None):
    
    session.save_session(g.CLIENT_STATE, g.CLIENT_STATE.get('SESSION_ID')) ## save the client state prior to sending sending data
    if g.HTTP_REDIRECT is not None:  ## something has set the global Redirect varaible clear output
        client_redirect(url=g.HTTP_REIRECT)  ## this was most likely already called eariler but we will call it again to make sure the headers are set
        poutput = '' #
    elif g.ERRORSSHOW or (pstatus != '200' and g.ERRORSSHOW):
        build_template('error', g.TEMPLATE_STACK.get('error'), False)
        error_context = {'Dump':dump_globals()}
        _ef = g.ENVIRO['TEMPLATE_CACHE_PATH'] + 'error' + g.TEMPALATE_EXTENSION

        _errorout = g.TEMPLATE_ENGINE(_ef,
                error_context,
                g.ENVIRO.get('TEMPLATE_TYPE'), 
                g.ENVIRO.get('TEMPLATE_TMP_PATH')
            )
        poutput = poutput.replace('</body>', _errorout + '</body>', 1)


    _head = list(pheaders.items()) # wsgi wants this as list 
    cc =[('Set-Cookie', str(v).strip() +";" ) for k, v in pcookies.items()] #put in the cookies 
    aa =[('Set-Cookie', g.COOKIES.output(attrs=None, header='', sep=''))]
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
    
    ##add the content length just before returning wsgi module
    _head.append( ('Content-Length', str(len(poutput))))
    sr(pstatus, _head)
    return [poutput]

def dump_globals():
    output = 'WebServer_ENVIRO \r\n'
    for key, value in sorted(g.APACHE_ENVIRO.items()):
        if value is not None:
            output += "%s %s \r\n " %(key,value)
    
    output += "\r\nAltered HTTP HEADERS \r\n "
    for key, value in sorted(g.HEADERS.items()):
        if value is not None:
            output += "%s %s \r\n " %(key,value)
    
    output += "\r\nCookies  \r\n "
    if len(g.COOKIES):
        for k, v in sorted(g.COOKIES.items()):
            output += 'Cookie Key = %s  value= %s' %(k, v)

    output += "\r\n \r\n APPLICATION ENVIROMENT \r\n"
    for key, value in  sorted(g.ENVIRO.items()):
        if value is not None:
            output += "%s:%s \r\n " %(key,value)

    if len(g.POST) > 0:
        output += "\r\n Converted POST commands\r\n" 
        for key, value in sorted(g.POST.items()):
            if value is not None:
                output += "%s:%s \r\n" %(key,value)

    if len(g.GET) > 0:
        output += "\r\n Converted GET commands\r\n" 
        for key, value in sorted(g.GET.items()):
            if value is not None :
                output += "%s:%s \r\n" %(key,value)

    if len(g.CONTEXT) > 0:
        output += "\r\n context\r\n" 
        for key, value in sorted(g.CONTEXT.items()):
            if value is not None and type(value) not in (list, dict, tuple) :
                output += "%s:%s \r\n" %(key,value)
    
    if len(g.COOKIES) > 0:
        output += "\r\n Cookies\r\n" 
        output += g.COOKIES.output(sep='\r\n')

    if len(g.APPSTACK) > 0:
        output += "\r\n Application Stack\r\n" 
        for key, value in sorted(g.APPSTACK.items()):
            if value is not None:
                output += "%s:%s \r\n" %(key,value)

    if len(g.TEMPLATE_STACK) > 0:
        output += "\r\n Template Stack\r\n" 
        for key, value in sorted(g.TEMPLATE_STACK.items()):
            if value is not None:
                output += "%s:%s \r\n" %(key,value)
    
    if len(g.ERRORSTACK):
        output += "\r\n Error Stack:\r\n"
        for _est in g.ERRORSTACK:
            output += "\r\n".join(_est)

    output += "\r\n Template to be Rendered: %s \r\n" % (g.TEMPLATE_TO_RENDER)
    output += "Security Context is not dumped \r\n"

    return output

def run_pyapp(papp_filename='', 
                papp_path='.', 
                papp_command='init', 
                ptemplate_stack='',
                pcontent_type='', 
                pcheck_CSB = True):
    """
    papp_filename: is the python module being dynamically imported 
    papp_path: is the path to the module it should follow python . notation
    papp_command: the function in the module that will be executed. 
    ptemplate_stack: template stack that is rendered by the app
    pcontect_type: html content type retuned to the browes 
    pcheck_CSB: this stage check the CSB entry to the one in the server if it does not no other 
    processing is done default is to check the CSB.

    the function must to return a boolean type.  if this function is called recursively 
    there is logic built in to redirect or call a different app to render a different result. 
    Method ONE is a recursive call must return False to prevent the Output buffer 
        from being re-rendered and just call run_pyapp setting the parameters as nessarcy 
    Method TWO return true set  the  global context  and template_stack varabiles to be rendered
    Method THREE is set the global varabel redirect which is check prior in the server return function, 
        clears the output buffer,  you can use a query string or users_session to do additional procesing

    Keep in mind the CSB entry may have already checked and deleted from the database there may be a need
    to set the pcheck_CSB to false on recurvise run_pyapp to allow additional processing  
    """
    if papp_filename == '':
        error('No App_name passed in Failed', 'run_pyapp')
        return False
    to_render =False
    ## try to find the template on the template link in the dictionary
    error( 'var pass = %s'% (ptemplate_stack), 'what value is passed into ptemplate_stacks')
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
        error("No Template Defined for %s " % ( papp_filename ), 'run_pyapp')
    
    #lets check the CSB key in the saved session if valid continue with the 
    #saved session from the database.  if not die 
    if not check_CSB(g.CSB):
        error('CSB has expired or is not present should redirect to root or login page the CSB created aknew')
    
    add_globals_to_Context()
    ar = importlib.import_module(papp_filename, papp_command) 
    if hasattr(ar, papp_command) : 
        if getattr(ar, papp_command)(): ##if the app returns false no template will be rendered
                    # logic here is so the calledpyapp can recursive call run_pyapp
                    # return false to block the rendering engine and clearing the output buffer.   
            if to_render :
                try :
                    g.CONTEXT.update({'CSB':save_CSB(g.SEC['USER_ID'])})
                    g.OUTPUT= g.TEMPLATE_ENGINE(g.TEMPLATE_TO_RENDER, 
                                g.CONTEXT, 
                                g.ENVIRO.get('TEMPLATE_TYPE'), 
                                g.ENVIRO.get('TEMPLATE_TMP_PATH'))
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

def add_globals_to_Context():
    #add the enviroment and headers 
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
    ## no root command has been setup 
    g.ENVIRO['URI_PATH_NOT_MATCHED']= g.ENVIRO['URI_PATH']
    return False

def check_app_in_appstack():
    if g.ENVIRO['PYAPP_TO_RUN'] in g.APPSTACK.keys():
        return True
    return False

def build_template(papp_name='', ptstack=[], pupdate_global=True ):
    _error_mess = ''
    if pupdate_global:
        g.TEMPLATE_TO_RENDER = g.ENVIRO['TEMPLATE_CACHE_PATH'] + papp_name + g.TEMPALATE_EXTENSION
    if template_cache_is_in(papp_name + g.TEMPALATE_EXTENSION):
        return True
    ## YES NOT pythonic but need to know if on first item in the list
    ## and can not pop it as it would alter this stack during run time 
    ## we do not want to do that...  
    _bts = ''
    for  _i in  ptstack: 
        _fp = g.ENVIRO['TEMPLATE_PATH']+_i 
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

def template_cache_is_in(pkey_value): #returns true if the cached file is found and set global template_to_render 
    ##todo is refactor the render engine to work on file like objects instead of paths
    ## this allow storing  pickled objects in memcache and use of spooled in memory temp files 
    _path = g.ENVIRO['TEMPLATE_CACHE_PATH']
    if g.ENVIRO['MEMCACHE_USE']:
        cached_file = g.MEMCACHE.get(pkey_value)
        if cached_file is None:
            return False
        tfile = open(_path+pkey_value, 'w+b')
        tfile.write(cached_file)
        tfile.close() 
        g.TEMPLATE_TO_RENDER = _path + pkey_value 
        return True    
    elif os.path.isfile(_path+pkey_value):
        fpath =  _path + pkey_value 
        age = dt.fromtimestamp(os.path.getmtime(fpath)) + td(seconds=g.ENVIRO['TEMPLATE_CACHE_AGING_SECONDS'])
        if dt.now() > age :
            os.remove(fpath)
            return False
        g.TEMPLATE_TO_RENDER = _path + pkey_value
        return True
    return False
    
def template_cache_put_in(key_value, content ):
    if g.ENVIRO['MEMCACHE_USE']:
        g.MEMCACHE.set(key_value, content) ##this will need more work to probably have to use pickle
    path = g.ENVIRO['TEMPLATE_CACHE_PATH']
    cfile = open(path+key_value, 'w')
    cfile.write(content)
    cfile.close()
    return True

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
    
    _co = session.load_cookies(e.get('HTTP_COOKIE'))
    if _co:
        if _co.get('session_id'): ##see if the session id is set and if we have previous get/post event to process
            for k, v in _co.items():
                g.COOKIES.update({k:v})
            ## load the session from the database if successful skip over  loading the GET and POST enviroments
            if session.load_session(_co.get('session_id')): 
                return True
    else : ##have no session established 
        session.create_session()     

    #Load Parse and Process the POST and GET commands
    script = ''
    command = ''
    qs =[]
    if e.get('REQUEST_METHOD').upper() == 'POST':
        script = ( e.get('REQUEST_URI', '').encode('iso-8859-1').decode(errors='replace') or
                e.get('SCRIPT_NAME', '').encode('iso-8859-1').decode(errors='replace') or 
                e.get('REDIRECT_URL', '').encode('iso-8859-1').decode(errors='replace')
            )
        g.POST.update({'url_path': script})
        g.POST.update({'POST_COUNT':0})
        try:
            request_body_size = int(e.get('CONTENT_LENGTH', 0))
        except (ValueError):
            request_body_size = 0
        if request_body_size > 0:
            form_data = parse_qs(e['wsgi.input'].read(request_body_size))
            for key, value in form_data.items():
                g.POST.update({bytes_to_text(key): [bytes_to_text(i) for i in value]})
                g.POST['POST_COUNT']+= 1
            g.CSB = g.POST.get('CSB', [0])[0]
        g.POST.update({'CONTENT_TYPE': e.get('CONTENT_TYPE')})
        return True
    elif e.get('REQUEST_METHOD').upper() == 'GET':
        _url = bytes_to_text(e.get('REQUEST_URI'))
        g.GET.update({"PATH_TO_APP":bytes_to_text(e.get('mod_wsgi.path_info')) })
        g.GET.update({'SCRIPT_ROOT':bytes_to_text( e.get('mod_wsgi.script_name'))})
        if _url is None:
            return True
        else :
            script = ( _url.encode('iso-8859-1').decode(errors='replace') or 
                        _url.encode('iso-8859-1').decode(errors='replace')
                    )      
        g.GET.update({'url_path': script})
        qs = e.get('QUERY_STRING')
        g.GET.update({'QUERY_STRING_COUNT':0})
        if isinstance(qs, bytes): ##url encoded data typically ascii
            try:
                qs = parse_qs(qs.decode(g.ENVIRO['ENCODING']))
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
        return True
    return False

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

def bytes_to_text(_p, encode=g.ENVIRO['ENCODING']):
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

def build_template_key(pdic={}, pout='file.ctemplates', ptype='file' ):
    
    if isinstance(pdic, dict):
        _r = break_apart_dic(pdic)

def break_apart_dic(pdic={}, p_prefix=''):
    _output = ''
    if isinstance(pdic, dict):
        for key, value in sorted(pdic.items()):
            #print (p_prefix + '.'+ key+ '.' +str(value))
            if isinstance(value, list):
                _output = _output + break_apart_dic(value, key)
            elif p_prefix >'' and isinstance(value,dict):
                _output = _output + break_apart_dic(value, p_prefix + '.' + key)
            elif isinstance(value, dict):
                _output = _output +  break_apart_dic(value, key )
            else:
                _output = _output + '<TMPL_VAR name="%s"> %s' % (p_prefix + '.' + key, chr(10))
    elif isinstance(pdic, list):
        _output = '<TMPL_LOOP name="%s"> %s %s' % (p_prefix, chr(10), chr(9))
        for i in value:
            if isinstance(i, dict):
                _output + (break_apart_dic(i, p_prefix ))
        _output = _output + '%s</TMPL_LOOP>' +chr(10) 
    return _output 

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

#print(break_apart_dic(g.APPSTACK, '' ))
