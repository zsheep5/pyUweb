import globals as g 
import pyUweb as m 
import session_controller as sc


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

def show_errors():
    if sc.check_credentials('errors') :
        return load_render_error_template(dump_secured_error_stack())
    else : 
        return load_render_error_template(dump_unsecured_error_stack())

def load_render_error_template(pcontext):

    if m.build_template('error', g.TEMPLATE_STACK.get('error'), False):
    
        _ef = g.ENVIRO['TEMPLATE_CACHE_PATH'] + 'error' + g.TEMPALATE_EXTENSION

        return g.TEMPLATE_ENGINE(_ef,
                pcontext,
                g.ENVIRO.get('TEMPLATE_TYPE', ''), 
                g.ENVIRO.get('TEMPLATE_TMP_PATH', '')
            )