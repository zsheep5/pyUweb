#import bleach
#import html_sanitizer

def escape_html(pstring,
                pescape_map={"&": "&amp;", 
                             '"': "&quot;", "'":"&apos;",
                             ">":"&gt;", "<": "&lt;"
                            }
                ):
    ##deal with the & first then pop it out of the dictionary     
    _amp = pescape_map.get('&', None)
    if _amp is not None:
        pstring = pstring.replace('&', _amp)
    for _k, _v in pescape_map.items():
        pstring = pstring.replace(_k, _v)
    return pstring

def html_combobox(plist=[], name='', id=''):
    _r = '<select id="%s" name="%s">' %(id,name)
    for l in plist :
        for _k, _v in l.items():
            _r = _r + '<option value="'+ str(_v) + '">' + _k + '</option>' 
    return  _r + '</select>'

def html_combobox_from_dic(pdic={}, name='', id=''):
    _r = '<select id="%s" name="%s">' %(id,name)
    for _k, _v in l.items():
        _r = _r + '<option value="'+ str(_v) + '">' + _k + '</option>' 
    return  _r + '</select>'
