import globals as g
import pyUwf as m
import psycopg2, psycopg2.extras
from http.cookies import SimpleCookie as sCookie
from http.cookies import Morsel  
from html2text import html2text as extext
from urllib.parse import quote_plus as qp 
from datetime import datetime as dt 
from datetime import timedelta as td

##session.controller.py contains the parts generate the login page and functions for controlling
## the user_session and saving the session. 


def check_credentials(papp_to_run = '', user_id= -1):
    ##first step lets see if the user must be logged in 
    if isinstance( g.ENVIRO['PYAPP_TO_RUN'],list ):
        if load_credentials() and check_user_credtials(g.SEC):
                return m.client_redirect(g.APPSTACK['login'], 307, 
                    'Application requires Security log in please')
    return True

def check_user_credtials(sec={}):
    return True

def load_login_page():
    save_session()
    ##clear the context and outputs
    g.CONTEXT={}
    g.CONTEXT.update({"user_name":g.COOKIES.get('user_name')})
    g.OUTPUT = ''
    m.build_template('log_in', g.TEMPLATE_STACK.get('log_in'))

    return True

def log_in():
    pass

def load_session(p_session_id = None, p_con=None):
    """ Returns true if stored session loads and retry command is set
    else returns false load enviroment should finish as normal
    """
    if p_con is None:
        p_con = m.get_db_connection()
    if p_session_id is None or not hasattr(p_session_id, 'value') :
        create_session()
        return False
    else:
        if p_session_id.value.isdigit() == False:
            return False
        q_str =""" select cs_data from client_state 
            where cs_id = %(session_id)s """
        _cur = p_con.cursor()
        _cur.execute(q_str,{'session_id':p_session_id.value})
        _r = _cur.fetchall()
        if len(_r) ==0: ##the database does not have the session data create a new one
            create_session()
            return False
        _session = _r[0][0]
        g.CLIENT_STATE = _session ##set the global client_state = to the one stored in the database
        if _session.get('TIMEOUT')< dt.utcnow() \
                and g.ENVIRO.get('PYAPP_TO_RUN').get('security') \
                and not g.SEC['USER_AUTOLOGIN']:
            ## the session has timeout and the app to run requiries security and 
            # the user auto login is turned off go to log in
            m.error('Seesion Id %s timeout, redirect to login script ')
            g.CLIENT_STATE.update({'last_command':'retry'})
            g.CLIENT_STATE.update({'PYAPP_TO_RUN':g.ENVIRO.get('PYAPP_TO_RUN')})
            g.CLIENT_STATE.update({'POST':g.POST})
            g.CLIENT_STATE.update({'GET':g.GET})
            return m.client_redirect(None, 0, 'Session Timeout log in please')
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
    session_id = m.get_db_next_id('client_state_cs_id_seq')
    set_cookie('session_id', session_id)
    g.CLIENT_STATE.update({'SESSION_ID': session_id})
    g.CLIENT_STATE.update({'TIMEOUT': dt.utcnow() + td(seconds=g.SEC['USER_TIMER'])})

def save_session(pdict=None, p_session_id=None, p_last_command='retry', p_con=None):
    if p_con is None:
        p_con = m.get_db_connection()
    _cur = p_con.cursor()

    if p_session_id is None:
        p_session_id = m.get_db_next_id('client_state_cs_id_seq')
    
    if pdict is None:
        pdict = g.CLIENT_STATE

    if p_last_command == 'retry':
        pdict.update({'last_command':'retry' })
        pdict.update({'PYAPP_TO_RUN':g.ENVIRO.get('PYAPP_TO_RUN')})
    ##got get 
    pdict.update( {'TIMEOUT' : str(dt.utcnow() + td(seconds=g.SEC['USER_TIMER']))})
    pdict.update({'POST': g.POST})
    pdict.update({'GET': g.GET})
    from json import dumps
    q_sql = """ insert into client_state values (
                %(p_session_id)s, %(pdict)s  )
                on conflict (cs_id) do Update
                set cs_data = %(pdict)s
             """
    _cur.execute(q_sql, {'p_session_id': p_session_id,
                        'pdict': dumps(pdict) 
                        })
    p_con.commit()

def load_credentials(puser='', pwd='', p_con=None):
    if p_con is None:
        p_con = m.get_db_connection()
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

def set_cookie(pname='', pvalue='', pexpires=None, pdomain=None,
              psecure=False, phttponly=False, ppath=None):
    """Sets a cookie."""
    morsel = Morsel()
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

def load_cookies(pcookie_string = None) :
    g.COOKIES = sCookie()
    g.COOKIES.load(pcookie_string)
    return g.COOKIES

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
