import pyUwf as m 
#import globals as g 
import session_controller as sc
import traceback, sys, os


def dump_secured_error_stack():
    return {'Dump':dump_globals()}

def dump_unsecured_error_stack():
    return 'An Error occured and can process your request'


def dump_globals():  ##convert the globals So there easy to print out HTML rendering engine
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

def show_errors(et='', pe=None, ENVIRO={}, TEMPLATE_ENGINE=None, 
            POST={}, 
            GET={}, 
            CLIENT_STATE={},  
            COOKIES={}, 
            CONTEXT={},
            CSB='',
            TEMPLATE='', 
            ):
    
    if pe is None or not isinstance(pe, Exception):
        return ""
    if len(et)==0:
        return ""
    
    _exc_type, _exc_value, _exc_traceback = sys.exc_info()
    _eslist = traceback.format_tb(_exc_traceback)
    _post = m.check_dict_for_list(POST)
    _get = m.check_dict_for_list(GET)
    _context = m.add_to_Context({}, _post, _get, ENVIRO, CLIENT_STATE, COOKIES,  TEMPLATE, CSB)
    _context.update({'CALL_STACK':tb_list_of_dicts('ERROR_STACK', _eslist)})
    _context.update({'EXCEPTION_CLASS_NAME:':repr(pe)})
    _context.update({'EXCEPTION':str(pe)})
    _context.update({'CALL_STACK_LENGTH':len(_eslist)+1})
    _output = TEMPLATE_ENGINE( et, 
                    _context, 
                    'string', 
                    ENVIRO.get('TEMPLATE_CACHE_PATH_POST_RENDER', os.getcwd())
                )
    return True, _output

def tb_list_of_dicts(pkey, plist):
    _rldic = []
    for _i in plist:
        _rldic.append({pkey:_i})
    return _rldic

def load_render_error_template(pcontext, pt):

    if m.build_template('error', g.TEMPLATE_STACK.get('error'), False):
    
        _ef = g.ENVIRO['TEMPLATE_CACHE_PATH'] + 'error' + g.TEMPALATE_EXTENSION

        return g.TEMPLATE_ENGINE(_ef,
                pcontext,
                g.ENVIRO.get('TEMPLATE_TYPE', ''), 
                g.ENVIRO.get('TEMPLATE_TMP_PATH', '')
            )