import psycopg2, psycopg2.extras
import cgi, os, importlib, time
import pyctemplate   #template engine
from urllib.parse import urlparse, urlencode
from zlib import adler32
import globals as g 
from datetime import datetime as dt 
from datetime import timedelta as td
from http.cookies import SimpleCookie as sc
from http.cookies import Morsel as mc
import uuid

##this is the main driving function it runs the below start up functions
# if all are true it then searches for the app to be called then processes it
#      
def kick_start(enviro, start_response):
    if not check_paths():
        return server_respond(pstatus='500 ', 
            poutput='Can not connect to the Database', pre=None,
            sr=start_response)
    else:
        append_to_sys_path()
    if not connect_to_db(pwd='123456'):
        return server_respond(pstatus='500 ', 
            poutput='Can not connect to the Database', pre=None,
            sr=start_response)
    elif not load_enviro(enviro):
        return server_respond(pstatus='500 ', 
            poutput='load enviro', pre=None, sr=start_response)
    elif not check_SSL(enviro):
        return server_respond(pstatus='500 ', 
            poutput='SSL Check failure', pre=None, sr=start_response)
    elif not match_uri_to_app():
        return server_respond(pstatus='500 ', 
            poutput='URI did not match to anything on this server', pre=None,
            sr=start_response)
    else:
        _ap =  g.ENVIRO['PYAPP_TO_RUN']
        _test = run_pyapp ( 
                papp_filename = _ap['filename'], 
                papp_path =     _ap['path'],
                papp_command=   _ap['command'], 
                ptemplate_stack=_ap['template_stack'],
                pcontent_type=  _ap['content_type']
            )
        if _test:
            return server_respond( poutput=g.OUTPUT, pre=None, 
            sr=start_response)
    save_client_state()
    
    return server_respond(pstatus='500 ', 
        pcontext=[], 
        pheaders={'Content-type': 'text/plain'}, 
        pre=None, 
        poutput='Internal Server Error No Command Sent',
        sr=start_response
        )

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
        sr = None): 
    

    if g.ERRORSSHOW or (pstatus != '200' and g.ERRORSSHOW):
        build_template('error', g.TEMPLATE_STACK.get('error'), False)
        error_context = {'Dump':dump_globals()}
        _ef = g.ENVIRO['TEMPLATE_CACHE_PATH'] + 'error' + g.TEMPALATE_EXTENSION
        poutput += g.TEMPLATE_ENGINE(_ef,
                error_context,
                g.TEMPLATE_TYPE, 
                g.TEMPLATE_TMP_PATH
            )

    _head = list(pheaders.items()) # wsgi wants this as list 
    _head.extend( [('Set-Cookie', str(v).strip() +";" ) for k, v in pcookies.items()]) #put in the cookies 
    _outputB = poutput.encode(encoding='utf-8', errors='replace')

    ##add the content length just before returning wsgi module
    _head.append( ('Content-Length', str(len(_outputB))))
    sr(pstatus, _head)
    return [_outputB]

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
            if value is not None:
                output += "%s:%s \r\n" %(key,value)

    if len(g.CONTEXT) > 0:
        output += "\r\n context\r\n" 
        for key, value in sorted(g.CONTEXT.items()):
            if value is not None:
                output += "%s:%s \r\n" %(key,value)

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


## papp_filename is the python module being dynamically imported 
## papp_path is the path to the module it should follow python . notation
## papp_command the function in the module that will be executed. 
## the function needs to return a boolean type 
## the function should make changes to the global variables set in
## globals.py file.  
def run_pyapp(papp_filename='', 
                papp_path='.', 
                papp_command='init', 
                ptemplate_stack='',
                pcontent_type='' ):
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
    
    
    add_globals_to_Context()
    ar = importlib.import_module(papp_filename, papp_command) 
    if hasattr(ar, papp_command) : 
        getattr(ar, papp_command)()
        if to_render :
            try :
                g.OUTPUT= g.TEMPLATE_ENGINE(g.TEMPLATE_TO_RENDER, 
                            g.CONTEXT, 
                            g.TEMPLATE_TYPE, 
                            g.TEMPLATE_TMP_PATH)
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
    g.CONTEXT.update({'IMAGES':g.ENVIRO['IMAGES']})
    g.CONTEXT.update({'DOCS':g.ENVIRO['DOCS']})
    g.CONTEXT.update({'STATIC':g.ENVIRO['STATIC']})
    g.CONTEXT.update({'MEDIA':g.ENVIRO['MEDIA']})
    g.CONTEXT.update({'SITE_NAME':g.ENVIRO['SITE_NAME']})
    g.CONTEXT.update({'URL':'http://'+g.ENVIRO['URL']})
    g.CONTEXT.update({'URLS':'https://'+g.ENVIRO['URL']})
    g.CONTEXT.update({'APPURL':g.ENVIRO['PROTOCOL'] + g.ENVIRO['URL'] + g.ENVIRO['SCRIPT_NAME']} )
    g.CONTEXT.update({'sec':g.SEC})
    g.CONTEXT.update({'CSB':g.CSB})
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
    if '/' in g.APPSTACK:
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
    error('enter_build_template' )
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
        error(_rstring)
        if os.path.isfile(_fp):
            _tp = open(_fp, 'r')
            _tp.seek(0)
            if _bts.find(_rstring) == -1:
                _bts += _tp.read()
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

    g.ENVIRO['PROTOCOL']= 'http://'
    g.ENVIRO['STATIC']['furlpath']=g.ENVIRO['PROTOCOL']+g.ENVIRO['URL']+g.ENVIRO['STATIC']['urlpath']
    g.ENVIRO['IMAGES']['furlpath']=g.ENVIRO['PROTOCOL']+g.ENVIRO['URL']+g.ENVIRO['IMAGES']['urlpath']
    g.ENVIRO['DOCS']['furlpath']=g.ENVIRO['PROTOCOL']+  g.ENVIRO['URL']+g.ENVIRO['DOCS']['urlpath']
    g.ENVIRO['MEDIA']['furlpath']=g.ENVIRO['PROTOCOL']+ g.ENVIRO['URL']+g.ENVIRO['MEDIA']['urlpath']
    
    _co = None
    if e.get('HTTP_COOKIE'):
        _co = sc()
        _co.load(e.get('HTTP_COOKIE'))
        if _co.get('session_id'): ##see if the session id is set and if we have previous 
            
            for k, v in _co.items():
                g.COOKIES.update({k:v})
            ## load the session from the database if successful skip over te load enviro.  
            if load_session(_co.get('session_id')):  ## this always set session id
                return True
         

    script = ''
    command = ''
    qs =[]
    if e.get('REQUEST_METHOD').upper() == 'POST':
        script = ( e.get('SCRIPT_URL').encode('iso-8859-1').decode(errors='replace') or 
            e.get('REDIRECT_URL').encode('iso-8859-1').decode(errors='replace')
            )
        g.POST.update({'url_path': script})
        g.POST.update({'POST_COUNT':0})
        try:
            request_body_size = int(e.get('CONTENT_LENGTH', 0))
        except (ValueError):
            request_body_size = 0
        if request_body_size > 0:
            form_data = cgi.parse_qs(e['wsgi.input'].read(request_body_size))
            for key, value in form_data:
                g.POST.update({bytes_to_text(key): bytes_to_text(value)})
                g.POST['POST_COUNT']+= 1

        g.POST.update({'CONTENT_TYPE': cgi.parse_header(e.get['CONTENT_TYPE'])})
        if check_CSB(g.POST.get('CSB')):
            return True
        return False
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
                qs = cgi.parse_qsl(qs.decode(g.ENVIRO['ENCODING']))
            except UnicodeDecodeError:
                # ... but some user agents are misbehaving :-(
                qs = cgi.parse_qsl(qs.decode('iso-8859-1'))
        else:
            qs=cgi.parse_qsl(qs)
        if len(qs) > 0:
            for key, value in qs:
                g.GET.update({
                    bytes_to_text(key) :
                    bytes_to_text(value)
                })
                g.GET['QUERY_STRING_COUNT']+=1
        if check_CSB(g.GET.get('CSB')):
            return True
        return False
    return False

def check_CSB(pcsb):
    q_str =""" select true from csb
	            where csb_id = %(pcsb)s 
                and csb_expires > now()""";
    _cur = CONN.get('PG1').cursor()
    _cur.execute(q_str,{'pcsb':pcsb})
    _r = _cur.fetchall()
    if len(_r) > 0:
        _return = True
    else:
        _return = False
    q_str = """ delete from csb where csb_id = %(pcsb)s """
    _cur.execute(q_str,{'pcsb':pcsb})
    _cur.commit()
    return _return 


def save_CSB(pcsb):
    q_str =""" insert into csb values ( %(session_id)s 
                now() + interval '30 minutes' )""";
    _cur = g.CONN.get('PG1').cursor()
    g.CSB = uuid.uuid1().hex
    _cur.execute(q_str,{'session_id': g.SEC['USER_ID']+ g.CSB})
    _cur.commit()
    return True

def bytes_to_text(_p, encode=g.ENVIRO['ENCODING']):
    if isinstance(_p, bytes):
       return str(_p, encode, 'replace')
    return _p

def connect_to_db(host='127.0.0.1', 
                    db='g_family', 
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

def set_cookie(pname='', pvalue='', pexpires=None, pdomain=None,
              psecure=False, phttponly=False, ppath=None):
    """Sets a cookie."""
    morsel = mc()
    name, value = str(pname), str(pvalue)
    morsel.set(name, value, value)
    morsel['expires'] = pexpires or  (dt.utcnow() + td(seconds=g.COOKIES_EXPIRES)).strftime('%a, %d %b %Y %H:%M:%S %Z') 
    morsel['path'] = ppath or g.ENVIRO.get('URI_PATH')
    if pdomain:
        morsel['domain'] = pdomain
    if psecure:
        morsel['secure'] = psecure
    value = morsel.OutputString()
    if phttponly:
        value += '; httponly'
    g.COOKIES.update({name:value}) 

def check_credentials(papp_to_run = '', user_id= -1):
    ##first step lets see if the user must be logged in 
    if isinstance( g.ENVIRO['PYAPP_TO_RUN'],list ):
        if load_credentials() and check_user_credtials(g.SEC):
                return client_redirect(g.APPSTACK['login'], 307, 
                    'Application requires Security log in please')
    return True
    
def log_in_page():
    save_client_state()
    ##clear the context and outputs
    g.CONTEXT={}
    g.CONTEXT.update({"user_name":g.COOKIES.get('user_name')})
    g.OUTPUT = ''
    build_template('log_in', g.TEMPLATE_STACK.get('log_in'))

    return True

def log_user_in():
    pass

def load_session(p_session_id = None, p_con=None):
    """ Returns true of stored session loads and retry command is set
    else returns false load enviroment should finish as normal
    """
    if p_con is None:
        p_con = get_db_connection()
    if p_session_id is None or not hasattr(p_session_id, 'value') :
        create_session()
        return False
    else:
        if p_session_id.value.isdigit() == False:
            return False
        q_str =""" select cs_data from client_state 
            where cs_id = %(session_id)s """;
        _cur = p_con.cursor()
        _cur.execute(q_str,{'session_id':p_session_id.value})
        _r = _cur.fetchall()
        if len(_r) ==0: ##the database does not have the session data create a new one
            create_session()
            return False
        _session = _r[0][0]
        g.CLIENT_STATE = _session ##set the global client_state = to the one stored in the database
        if _session.get('TIMEOUT')< dt.utcnow() and g.ENVIRO.get('PYAPP_TO_RUN').get('security'):
            ## the session has timeout and the app to run requiries security redirect to log in
            error('Seesion Id %s timeout, redirect to login script ')
            g.CLIENT_STATE.update({'last_command':'retry'})
            g.CLIENT_STATE.update({'PYAPP_TO_RUN':g.ENVIRO.get('PYAPP_TO_RUN')})
            g.CLIENT_STATE.update({'POST':g.POST})
            g.CLIENT_STATE.update({'GET':g.GET})
            return client_redirect(g.APPSTACK['login'], 307,'Session Timeout log in please')
        elif _session.get('TIMEOUT')< dt.utcnow() and g.SEC['USER_AUTOLOGIN']:
            ## session has timeout but the autologin is turned on so log the user in and continue
            if load_credentials(g.COOKIES['user'], g.COOKIES['pwd']):
                if _session['last_command'] == 'retry':
                    g.ENVIRO.update({'PYAPP_TO_RUN':_session.get('PYAPP_TO_RUN')})
                    g.POST= _session.get('POST')
                    g.GET = _session.get('GET')
                    return True
        else:
            return False
    return False

def create_session():
    session_id = get_db_next_id('client_state_cs_id_seq')
    set_cookie('session_id', session_id)
    g.CLIENT_STATE.update({'SESSION_ID': session_id})
    g.CLIENT_STATE.update({'TIMEOUT': dt.utcnow() + td(seconds=g.SEC['USER_TIMER'])})

def save_client_state(pdict=g.CLIENT_STATE, p_session_id=None, p_last_command='retry', p_con=None):
    if p_con is None:
        p_con = get_db_connection()
    _cur = p_con.cursor()

    if p_last_command == 'retry':
        pdict.update({'last_command':'retry' })
        pdict.update({'PYAPP_TO_RUN':g.ENVIRO.get('PYAPP_TO_RUN')})
    ##got get 
    pdict.update( {'TIMEOUT' : dt.utcnow() + td(seconds=g.SEC['USER_TIMER'])})
    pdict.update({'POST': g.POST})
    pdict.update({'GET': g.GET})
    from json import dump
    q_sql = """ insert into client_state values (
                %(p_session_id)s, %(pdict)s  )
                on conflict do Update
                set cs_data = %(pdict)s
             """
    _cur.execute(q_sql, {'p_session_id': p_session_id,
                        'pdict': dump(pdict) 
                        })
    _cur.commit()

def load_public_credentials():
    pass

def load_credentials(puser='', pwd='', p_con=None):
    if p_con is None:
        p_con = get_db_connection()
    _cur = p_con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    q_str ="""select user_id user_name, user_last , user_email ,
                 user_type, user_pwd from users
                 where crypt( %(pwd)s, user_pwd)
                 and user_id = (%puser)s
            """
    _cur.execute(q_str, {'pwd':pwd, 'puser':puser})
    _rec = _cur.fetchall()
    if len(_rec) > 0:
        _r=_rec[0]
        g.SEC.update({'USER_ID':_r['user_id']})
        g.SEC.update({'USER_NAME':_r['user_name']+ ' ' +_r['user_last']})
        g.SEC.update({'USER_EMAIL':_r['user_email']})
        g.SEC.update({'USER_PWD':_r['user_pwd']})
        g.SEC.update({'USER_LOGGEDIN':True})
    else:
        return False

    q_str ="""select distinct  sa_app_name || '.' || sa_app_function,
                    sa_allowed 
                from (
                        select sa_app_name, sa_app_function, 
                            sa_allowed
                        from users
                        left join sec_access on 
                            sa_target_id = user_id
                            and sa_target_type = 'user'
                            and sa_allowed=true
                        where user_id = %(user_id)s
                    union 
                    select sa_app_name, sa_app_function, 
                            sa_allowed
                        from sec_groups
                        left join sec_access on
                            sa_target_id = sg_id
                            and sa_target_type = 'group'
                            and sa_allowed=true
                        where %(user_id)s =all(sg_members) 
                    ) sa """

    _cur.execute(q_str,{'user_id':_r['user_id']})
    _r = _cur.fetchall()   

def load_client_state():
    pass

def check_SSL(e):
    if g.SEC['SSL_REQUIRE']:
        if e.get('HTTPS', 'off') in ('on', '1'):
            return client_redirect('/ssl_requried', 
                '307 Temporary Redirect', b'')       
    return True

def client_redirect(url='', redirect_code='307', output=''): # sets the globals up 
    #for a redirect returns false as the kick_start needs to see false to 
    # return to wsgi out of sequence
    g.OUTPUT = output
    g.HEADERS['status'] = redirect_code + 'Location:' + url 
    return False 

def log_event(mess, level='DEBUG'):
    import logging
    logs = logging()
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

def cookies_tuple_string(p_cdic={}):
    _return=[]
    for _k, _v in sorted(p_cdic.items()):
        vstring = _k + '=' + _v['value'] +';'
        if isinstance(_v['expires'], dt):
            vstring += ' Expires=%s;' %(dt.strftime('%a, %d %b %Y %H:%M:%S %Z') )
        if len(_v['domain'])>0:
            vstring += ' Domain=%s'%(_v['domain'])
        if _v['secure']:
            vstring += ' Secure;'
        if len(_v['urlpath'])>0:
            vstring += 'Path=%s;'%(_v['urlpath'])
        _return.append(('Set-Cookie: ',vstring))
    return _return

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

def build_get_url(p_com='', p_dict={}, p_des= '', 
    p_base_url=g.ENVIRO['PROTOCOL'] + g.ENVIRO['URL'] + g.ENVIRO['SCRIPT_NAME'] ):
    """
        Takes in a distionary converts the keys to adler checksum
    """
    if len(p_dict) ==0:
        return None
    #url_dict={}
    #for key, value in sorted(pdic.items()):
        #url_dict.update({hex(adler32(key)):value})

    return 'p_base_url' + p_com + '?' + urlencode(p_dict)

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
        if not os.path.exists(g.TEMPLATE_TMP_PATH):
            os.makedirs(g.TEMPLATE_TMP_PATH, 0o755)

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

#print(break_apart_dic(g.APPSTACK, '' ))
