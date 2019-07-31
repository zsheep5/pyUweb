import globals as g
import pyUwf as m
import psycopg2, psycopg2.extras
import json
from http.cookies import BaseCookie as bCookie
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
    ##reset the context 
    m.add_globals_to_Context()
    g.CONTEXT.update({"user_name":g.COOKIES.get('user_name')})
    #Change the  template to be rendered
    m.build_template('log_in', g.TEMPLATE_STACK.get('log_in'))

    return True

def log_in():
    if g.POST.get('user_name') and g.POST.get('pwd'):
        if load_credentials(g.POST.get('user_name',[0])[0],  g.POST.get('pwd',[0])[0] ):
            ##set the current session so it knows its logged in
            if g.CLIENT_STATE.get('last_command') =='retry':
                load_prev_state(g.CLIENT_STATE.get('prev_state'))
                _ap=  g.ENVIRO.get('PYAPP_TO_RUN')
                return m.run_pyapp( 
                    papp_filename= _ap['filename'],
                    papp_path=     _ap['path'],
                    papp_command=   _ap['command'],
                    ptemplate_stack=_ap['template_stack'],
                    pcontent_type=  _ap['content_type']
                )
            ##have no previouse state to restore go back to the root
            _ap = g.APPSTACK['/']
            return m.run_pyapp( 
                    papp_filename= _ap['filename'],
                    papp_path=     _ap['path'],
                    papp_command=   _ap['command'],
                    ptemplate_stack=_ap['template_stack'],
                    pcontent_type=  _ap['content_type']
                )
    else:
        return load_login_page()

def change_pwd_page():
    if g.POST.get('user_name') and g.POST.get('current_pwd')  and g.POST.GET('new_pwd') and g.POST.get('confirm'):
        if load_credentials(g.POST.get('user_name'), g.POST.get('pwd') ) == False : 
            return False 
        if g.POST.GET('new_pwd') != g.POST.get('confirm'): 
            m.error('New passwords do not match can not change', 'session_controller.py function change_pwd_page')
        if change_pwd( g.POST.get('user_name'), g.POST.GET('new_pwd')):
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
        ##set the global client_state = to the one stored in the database
        _timeout = dt.strptime(_session.get('TIMEOUT'), '%Y-%m-%d %H:%M:%S.%f')
        _session.update({'TIMEOUT':_timeout})
        g.CLIENT_STATE = _session
        if _timeout< dt.utcnow() \
                and g.ENVIRO.get('PYAPP_TO_RUN').get('security') \
                and not g.SEC['USER_AUTOLOGIN']:
            ## the session has timeout and the app to run requiries security and 
            # the user auto login is turned off go to log in
            m.error('Seesion Id %s timeout, redirect to login script ')
            save_session(g.CLIENT_STATE, p_session_id, 'retry')
            return m.client_redirect(None, 0, 'Session Timeout log in please')
        elif _session.get('TIMEOUT')< dt.utcnow() and g.SEC['USER_AUTOLOGIN']:
            ## session has timeout but the autologin is turned on so log the user in and continue
            if load_credentials(g.COOKIES['user'], g.COOKIES['pwd']):
                if _session['last_command'] == 'retry':
                    g.CLIENT_STATE.update({'last_command':'retry'})
                    g.CLIENT_STATE.update({'prev_state':_session})
                return True
        elif _timeout > dt.utcnow():
            g.SEC = _session.get('SEC')
            if len(_session.get('last_command','')) > 0:
                load_prev_state(_session)
                return True
    return False

def load_prev_state(p_session={}):
    if len(p_session)<1:
        return False
    else:
        g.POST=p_session.get('POST')
        g.GET=p_session.get('GET')
        g.ENVIRO.update({'PYAPP_TO_RUN':_session.get('PYAPP_TO_RUN')})
        g.CLIENT_STATE.update({'TIMEOUT': dt.utcnow() + td(seconds=g.SEC['USER_TIMER'])})

def create_session():
    """Gets the next session id from the database ans sets the global variable and cookie  """
    session_id = m.get_db_next_id('client_state_cs_id_seq')
    set_cookie('session_id', session_id, phttponly=True)
    g.CLIENT_STATE.update({'SESSION_ID': session_id})
    g.CLIENT_STATE.update({'TIMEOUT': dt.utcnow() + td(seconds=g.SEC['USER_TIMER'])})
    save_session(g.CLIENT_STATE, session_id, '', None)

def save_session(pdict=None, p_session_id=None, p_last_command='', p_con=None):
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
    ##post and  get should always hold the last set of commands.   
    pdict.update( {'TIMEOUT' : str(dt.utcnow() + td(seconds=g.SEC['USER_TIMER']))})
    pdict.update({'POST': g.POST})
    pdict.update({'GET': g.GET})
    pdict.update({'SEC':g.SEC})
    q_sql = """ insert into client_state values (
                %(p_session_id)s, %(pdict)s  )
                on conflict (cs_id) do Update
                set cs_data = %(pdict)s
             """
    _cur.execute(q_sql, {'p_session_id': p_session_id,
                        'pdict': json.dumps(pdict) 
                        })
    p_con.commit()

def load_credentials(puser='', pwd='', p_con=None):
    if p_con is None:
        p_con = m.get_db_connection()
    _cur = p_con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    q_str ="""select user_id, user_name, user_last , user_email ,
                 user_type, user_pwd, user_displayname from users
                 where crypt( %(pwd)s, user_pwd) = user_pwd
                 and (user_displayname = %(puser)s or user_email = %(puser)s)
            """
    _cur.execute(q_str, {'pwd':pwd, 'puser':puser})
    _rec = _cur.fetchall()
    if len(_rec) == 1:  ##if there is more than one record this a big problem with the database  
        _r=_rec[0]
        g.SEC.update({'USER_ID':_r['user_id']})
        g.SEC.update({'USER_NAME':_r['user_name']+ ' ' +_r['user_last']})
        g.SEC.update({'USER_EMAIL':_r['user_email']})
        g.SEC.update({'USER_PWD':_r['user_pwd']})
        g.SEC.update({'USER_LOGGEDIN':True})
        g.SEC.update({'DISPLAY_NAME':_r['user_displayname']})
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
    if len(_r) > 0:
        g.SEC = _r
        return True
    return False

def set_cookie(pname='', pvalue='', pexpires=None, pdomain=None,
              psecure=False, phttponly=False, ppath=None):
    """Sets a cookie."""
    morsel = Morsel()
    name, value = str(pname), str(pvalue)
    morsel.set(name, value, value)
    morsel['expires'] = pexpires or  (dt.utcnow() + td(seconds=g.COOKIES_EXPIRES)).strftime('%a, %d %b %Y %H:%M:%S %Z') 
    if ppath:
        morsel['path'] = ppath
    if pdomain:
        morsel['domain'] = pdomain
    if psecure:
        morsel['secure'] = psecure
    if phttponly:
        morsel['httponly'] = True
    g.COOKIES.update({name:morsel})

def load_cookies(pcookie_string=''):
    if pcookie_string =='' or pcookie_string is None:
        return None
    _t = bCookie()
    _t.load(pcookie_string)
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

def create_user(p_con, p_name, p_last, p_pwd, p_email='', p_type='user', 
                p_grp = 0, p_displayname='unknown'  ):
    if p_con is None:
        p_con = m.get_db_connection()

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
    con = p_con 
    cur = con.cursor()
    cur.execute(q_str, _topass)
    cur = p_con.cursor()
    cur.execute(q_str)
    p_con.commit()