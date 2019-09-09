import globals
import pyUwf as m
import psycopg2, psycopg2.extras
import json
from http.cookies import BaseCookie as bCookie
from http.cookies import Morsel  
from html2text import html2text as extext
from urllib.parse import quote_plus as qp 
from datetime import datetime as dt 
from datetime import timedelta as td
import uuid

global COOKIES_to_Send, COOKIES
COOKIES= bCookie()
COOKIES_to_Send = bCookie()
COOKIES_EXPIRES = 3000
SEC = {}
CSB =''
CSB_STATUS =False

##session.controller.py contains the parts generate the login page and functions for controlling
## the user_session and saving the session. 


def check_credentials(papp_to_run='', CLIENT_STATE={}):
    ##function assums SEC has been initialized.
    
    _app = CLIENT_STATE.get('APPSTACK', {})

    if _app.get('security', True): ## default to True if not defined it blocks access by default
        _ua = SEC.get('USER_ACCESS')
        if isinstance(_ua, dict): ## no creditianls are loaded return false
            return _ua.get(papp_to_run, False)
        return False
    return True

def check_user_credtials(_ua={}, p_user=-1):
    pass

def load_login_page(POST ={}, GET={}, plogin_message='', ENVIRO={}, CLIENT_STATE={}, 
                    COOKIES={}, CONTEXT={}, TEMPLATE='', TEMPLATE_ENGINE=None, CSB=''):
    save_session(CLIENT_STATE,  POST, GET, ENVIRO,  
                COOKIES, CONTEXT,  TEMPLATE)

    ##get the global contexts
    CONTEXT.update({'login_message': plogin_message})
    CONTEXT.update({"user_name":COOKIES.get('user_name')})
    #Change the  template to be rendered
    if len(TEMPLATE) == 0:
        _ts = m.match_template_to_app('log_in','log_in', 'session_controller', '.html')
        _is_in_cache, TEMPLATE, _template_name = m.build_template('log_in', _ts, True)

    _output = TEMPLATE_ENGINE(TEMPLATE,  
                            CONTEXT, 
                            'string', 
                            ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER','' )
                        )
    return True, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB                    

def log_in( POST ={}, GET={}, ENVIRO={}, CLIENT_STATE={}, COOKIES={}, CONTEXT={}, 
            TEMPLATE='', TEMPLATE_ENGINE=None, CSB='',
            p_redirect_app=None, 
            pload_prev_state=True, 
            plogin_message='Successfully Logged in ', 
            plogin_error= 'User and Password did match any of records please try again'):
    """ redirect_app: is the application state to redirect the client to after successfully loggin in
        pload_prev_state = load the save session state after succuessfly  loging in. Note redirect and  load previous state can not be sett at the same time
        load prev state takes precedences over the redirect
        plogin_message message to display on success 
        plogin_error message to display on errors 
    """ 
    _result, CLIENT_STATE = load_session(COOKIES.get('session_id',1))
    _message = plogin_message
    if POST.get('user_name') and POST.get('pwd'):
        if load_credentials(POST.get('user_name',[0])[0],  POST.get('pwd',[0])[0] ):
            ##set the current session so it knows its logged in
            if CLIENT_STATE.get('last_command', '') =='retry' and pload_prev_state==True:
                
                _result, POST, GET, ENVIRO, CLIENT_STATE, CSB,=load_prev_state(CLIENT_STATE)
                _ap= m.match_uri_to_app( ENVIRO.get('URI_PATH', ''), m.get_APPSTACK() ) 
                return m.run_pyapp( 
                    papp_filename= _ap['filename'],
                    papp_path=     _ap['path'],
                    papp_command=   _ap['command'],
                    ptemplate_stack=_ap['template_stack'],
                    pcontent_type=  _ap['content_type'],
                    POST=POST, 
                    GET=GET, 
                    ENVIRO=ENVIRO,
                    CLIENT_STATE=CLIENT_STATE,  
                    COOKIES=COOKIES, 
                    CONTEXT=CONTEXT,
                    CSB=CSB,
                    TEMPLATE='', 
                    TEMPLATE_ENGINE=TEMPLATE_ENGINE
                )
            ##have no previouse state to restore go back to the page root
            APPSTACK = m.get_APPSTACK()
            _ap = APPSTACK['/']
            return m.run_pyapp( 
                    papp_filename= _ap['filename'],
                    papp_path=     _ap['path'],
                    papp_command=   _ap['command'],
                    ptemplate_stack=_ap['template_stack'],
                    pcontent_type=  _ap['content_type'],
                    POST=POST, 
                    GET=GET, 
                    ENVIRO=ENVIRO,
                    CLIENT_STATE=CLIENT_STATE,  
                    COOKIES=COOKIES, 
                    CONTEXT=CONTEXT,
                    CSB=CSB,
                    TEMPLATE='', 
                    TEMPLATE_ENGINE=TEMPLATE_ENGINE
                )
            return False ##must return false now as 
        else:
            _message  = plogin_error
            ## can add more logic for reset password and fail count to lock the account that it maybe matching to
    return load_login_page(POST =POST, GET=GET, plogin_message=_message, ENVIRO=ENVIRO, CLIENT_STATE=CLIENT_STATE,
                            COOKIES=COOKIES, CONTEXT=CONTEXT,
                            TEMPLATE=TEMPLATE, TEMPLATE_ENGINE=TEMPLATE_ENGINE)

def change_pwd_page(POST={}, 
                    GET={}, 
                    ENVIRO={},
                    CLIENT_STATE={},  
                    COOKIES={}, 
                    CONTEXT={},
                    CSB={},
                    TEMPLATE='', 
                    TEMPLATE_ENGINE=None):
    if POST.get('user_name') and POST.get('current_pwd')  and POST.GET('new_pwd') and POST.get('confirm'):
        if load_credentials(POST.get('user_name'), POST.get('pwd') ) == False : 
            return False 
        if POST.GET('new_pwd') != POST.get('confirm'): 
            m.error('New passwords do not match can not change', 'session_controller.py function change_pwd_page')
        if change_pwd( POST.get('user_name'), POST.GET('new_pwd')):
            return True    

def change_pwd(p_userid, p_newpwd ) :
    
    q_str = "update users set user_pwd = %(pwd)s where  user_name = %(user)s"
    p_con = m.get_db_connection()
    _cur =  p_con.cursor()
    _cur.execute(q_str,{'user':p_userid, 'pwd':p_userid})
    if _cur.commit():
        return True
    else :
        m.error('Failed to update the user password', 'session_controller.py fucntion change_pwd')
    return False

def load_session(p_session_id = None, APPSTACK={}, ENVIRO={}, CLIENT_STATE={}):
    """ Returns true if stored session loads and retry command is set

    else returns false load enviroment should finish as normal
    """
    CLIENT_STATE.update({'APPSTACK':APPSTACK})
    if p_session_id is None or not hasattr(p_session_id, 'value') :
        create_session()
        return False,  CLIENT_STATE
    else:
        if p_session_id.value.isdigit() == False:
            return False, CLIENT_STATE
        q_str =""" select cs_data from client_state 
            where cs_id = %(session_id)s """
        _r=m.run_sql_command(q_str,{'session_id':p_session_id.value})
        if len(_r) ==0: ##the database does not have the session data create a new one
            create_session()
            return False,  CLIENT_STATE
        CLIENT_STATE.update({'PREV_STATE':_r[0]['cs_data']})
        ##set the global client_state = to the one stored in the database
        _timeout = dt.strptime(CLIENT_STATE.get('PREV_STATE',{}).get('TIMEOUT','' ), '%Y-%m-%d %H:%M:%S.%f')
        if _timeout is None :
            _timeout = dt.utcnow() - td(seconds=SEC['USER_TIMER'])
        CLIENT_STATE.update({'TIMEOUT':_timeout})
        
        _ctime = dt.utcnow()
        if _timeout< _ctime \
                and 'security' in ENVIRO.get('PYAPP_TO_RUN', None)  \
                and not SEC['USER_AUTOLOGIN']:
            ## the session has timeout and the app to run requiries security and 
            # the user auto login is turned off go to log in
            m.error('Seesion Id %s timeout, redirect to login script ')
            save_session(CLIENT_STATE, 'retry',)
            return False, CLIENT_STATE
        elif CLIENT_STATE.get('TIMEOUT')< _ctime and SEC.get('USER_AUTOLOGIN',False):
            ## session has timeout but the autologin is turned on so log the user in and continue
            _results, SEC = load_credentials(COOKIES.get('user', ''), COOKIES.get('pwd', '') )
            if _results:
                if CLIENT_STATE['last_command'] == 'retry':
                    CLIENT_STATE.update({'last_command':'retry'})
                    CLIENT_STATE.update({'prev_state':_session})
                return True, CLIENT_STATE
        elif _timeout > _ctime:
            _results, SEC = load_credentials(COOKIES.get('user', ''), COOKIES.get('pwd', '') )
            if len(CLIENT_STATE.get('last_command','')) > 0:
                return True, CLIENT_STATE
    return False, CLIENT_STATE

def load_CSB(POST={}, GET={}, SEC={}):
    _csb = POST.get('CSB', False)
    if _csb :
        CSB = csb
        return CSB
    _csb = GET.get('CSB', False)
    if _csb :
        CSB =_csb
        return CSB
    CSB = set_CSB(SEC.get('USER_ID', ''))
    return CSB

def load_prev_state(CLIENT_STATE={}):
    if len(p_session)<1:
        return False, {}, {}, {}, {}, {}
    else:
        ps = CLIENT_STATE.get('PREV_STATE', {})
        POST=ps.get('POST',{})
        GET=ps.get('GET',{})
        ENVIRO=ps.get('ENVIRO',{})
        ps.update({'TIMEOUT': dt.utcnow() + td(seconds=SEC['USER_TIMER'])})
        CSB=ps.get('CSB', '')
        APPSTACK=ps.get('APPSTACK',{})
    return True, POST, GET, ENVIRO, CLIENT_STATE, CSB, APPSTACK

def create_session(CLIENT_STATE={}, 
                POST={}, 
                GET={}, 
                ENVIRO={},  
                COOKIES={}, 
                CONTEXT={},):
    """Gets the next session id from the database and sets the global variable and cookie  """
    session_id = m.get_db_next_id('client_state_cs_id_seq')
    set_cookie('session_id', session_id, phttponly=True)
    CLIENT_STATE.update({'SESSION_ID': session_id})
    CLIENT_STATE.update({'TIMEOUT': dt.utcnow() + td(seconds=SEC.get('USER_TIMER', 600))})
    save_session(CLIENT_STATE, POST, GET, ENVIRO, COOKIES, CONTEXT, '')
    return True, CLIENT_STATE

def save_session(CLIENT_STATE={},  
                POST={}, 
                GET={}, 
                ENVIRO={},  
                COOKIES={}, 
                CONTEXT={}, 
                TEMPLATE=''
            ):
    if CLIENT_STATE.get('SESSION_ID', '') =='':
        CLIENT_STATE.update({'SESSION_ID':str(m.get_db_next_id('client_state_cs_id_seq'))})

    ##post and  get should always hold the last set of commands. 
    # when it reloads it places the previous POST and GET's in prev_state   
    CLIENT_STATE.update({'TIMEOUT' : str(dt.utcnow() + td(seconds=SEC.get('USER_TIMER',6000)))})
    CLIENT_STATE.update({'POST': POST})
    CLIENT_STATE.update({'GET': GET})
    q_sql = """ insert into client_state values (
                %(session_id)s, %(pdict)s  )
                on conflict (cs_id) do Update
                set cs_data = %(pdict)s
             """
    _rec = m.run_sql_command(q_sql, {'session_id':CLIENT_STATE.get('SESSION_ID'),
                        'pdict': json.dumps(CLIENT_STATE) 
                        })
    return _rec.get('state', False)
    
def load_credentials(puser='', pwd='' ):
    q_str ="""select user_id, user_name, user_last , user_email ,
                 user_type, user_pwd, user_displayname from users
                 where crypt( %(pwd)s, user_pwd) = user_pwd
                 and (user_displayname = %(puser)s or user_email = %(puser)s)
            """
    _rec = m.run_sql_command(q_str,  {'pwd':pwd, 'puser':puser} )
    user_id = 0
    SEC= {}
    if len(_rec) == 1:  ##if there is more than one record this a big problem with the database  
        _r =_rec[0]
        user_id = _r.get('user_id')
        SEC.update({'USER_ID':_r['user_id']})
        SEC.update({'USER_NAME':_r['user_name']+ ' ' +_r['user_last']})
        SEC.update({'USER_EMAIL':_r['user_email']})
        SEC.update({'USER_PWD':_r['user_pwd']})
        SEC.update({'USER_LOGGEDIN':True})
        SEC.update({'DISPLAY_NAME':_r['user_displayname']})
    else:
        return False, SEC

    q_str ="""select json_agg(
                        json_build_object( 
                            sa_app_name || '.' || sa_app_function ,
                            sa_allowed 
                        )
                    ) as security
                from (
                        select sa_app_name, sa_app_function, 
                            sa_allowed, 'from_users'
                        from users
                        inner join sec_access on 
                            sa_target_id = user_id
                            and sa_target_type = 'user'
                            and sa_allowed=true
                        where user_id = %(user_id)s
                    union 
                    select sa_app_name, sa_app_function, 
                            sa_allowed, 'from_groups'
                        from sec_groups
                        inner join sec_access on
                            sa_target_id = sg_id
                            and sa_target_type = 'group'
                            and sa_allowed=true
                        where %(user_id)s =all(sg_members) 
                    ) sa """

    _rec = m.run_sql_command(q_str, {'user_id':user_id })
    if len(_rec) ==1:
       SEC.update({'USER_ACCESS':_rec[0]['security']})
       return True, SEC
    return False, {}

def set_cookie(pname='', pvalue='', pexpires=None, pdomain=None,
              psecure=False, phttponly=False, ppath='/'):
    """Sets a cookie."""
    morsel = Morsel()
    name, value = str(pname), str(pvalue)
    morsel.set(name, value, value)
    morsel['expires'] = pexpires or  (dt.utcnow() + td(seconds=COOKIES_EXPIRES)).strftime('%a, %d %b %Y %H:%M:%S %Z') 
    if ppath:
        morsel['path'] = ppath
    if pdomain:
        morsel['domain'] = pdomain
    if psecure:
        morsel['secure'] = psecure
    if phttponly:
        morsel['httponly'] = True
    new_cookie(name,morsel)

def new_cookie(pkey,value):
    COOKIES.update({pkey:value})
    COOKIES_to_Send.update({pkey:value})

def load_cookies(pcookie_string=''):
    if pcookie_string =='' or pcookie_string is None:
        return False, {}
    _t = bCookie()
    _t.load(pcookie_string)
    return True, _t

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

def create_user(p_name, p_last, p_pwd, p_email='', p_type='user', 
                p_grp = 0, p_displayname='unknown'  ):
    q_str = """
        insert into users ( 
                user_id,
                user_name ,
                user_last,
                user_email ,
                user_type ,
                user_pwd ,
                user_grp,
                user_displayname )
            values
            ( default, %(name)s, %(last)s, %(email)s, %(type)s,
             crypt(%(pwd)s::text, gen_salt('md5')), %(grp)s, %(displayname)s),

    """
    _topass = {'name':p_name , 'last':p_last, 
                'pwd':p_pwd,  'email': p_email ,
                'type':p_type, 'grp':p_grp,
                'displayname': p_displayname 
            }
    _rec = m.run_sql_command(q_str, _topass)
    return _rec.get('state', False)

def check_CSB(pcsb):
    """ antime check_CSB called the database
    copy is purged from database regardless 
    if it is valid or expired 
    """ 
    q_str =""" select true from csb
	            where csb_id = %(pcsb)s 
                and csb_expires > now()"""
    _r = m.run_sql_command(q_str,{'pcsb':pcsb})
    if len(_r) > 0:
        _return = True
        CSB_STATUS=True
    else:
        _return = False
        CSB_STATUS=False
    q_str = """ delete from csb where csb_id = %(pcsb)s """
    m.run_sql_command(q_str,{'pcsb':pcsb})
    return _return 

def set_CSB(puser_id):
    q_str =""" insert into csb values ( %(session_id)s, 
                now() + interval '30 minutes' )"""

    CSB = uuid.uuid1().hex
    m.run_sql_command(q_str,{'session_id':str(puser_id)+ CSB})
    return CSB