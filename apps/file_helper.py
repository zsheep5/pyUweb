""" File helper is an app that takes in Files, blob, images, text or any other file type saves it to the database 
and writes the file out to disk to be servered by the webserver. 
""" 
import session_controller as sc
import pyUwf as m
import psycopg2, psycopg2.extras 

def get_file_from_db(p_con=None, p_image_id=-1, p_path='', p_type='file,string' ) :

    _sql = "select file_name, file_type, file_stream from files where file_id= %(p_image_id)s "

    _r = m.run_sql_command(p_con,_sql, {'p_image_id': p_image_id})
    if len(_r)!=1:
        return None
    
    if p_type == 'file':
        _temp = open(p_path + str(p_image_id) + '_' + _r[0][0] + '.' + _r[0][1], 'rb')
        _temp.write(_r[0][2])
        _temp.flush()
        _temp.seek(0)
        return _temp
    
    if p_type == 'string':
        return _r[0][2]

def write_file_to_db(p_con=None, p_image_id=-1, p_user_id=-1, p_fname ='', p_type='', p_fstream=''):

    if p_image_id ==-1:
        _holder = 'default'
    else :
        _holder = str(p_image_id)

    _sql = "Insert into files values( "+_holder+", %(p_fname)s, %(p_user_id)s, now(), %(p_type)s, %(p_fstream)s )"
    _sql = _sql + """on conflict (file_id) do Update set
             file_name = %(p_fname)s, 
             file_type = %(p_type)s , 
             file_stream= %(p_fstream)s returning file_id"""

    _r = m.run_sql_command(p_con,_sql, {'p_fname': p_fname,
                                      'p_type':p_type,
                                      'p_fstream': p_fstream,
                                      'p_user_id':p_user_id,
                                    })
    return _r

def dump_files_to_disk(p_con=None, p_path=''):
    """ Dumps all files saved in the DB to p_path  or current working directory"""

    _sql = "select file_id ,file_name, file_type, file_stream from files "

    _r = m.run_sql_command(p_con,_sql)

    for _e in _r:
        _w = m.run_sql_command(p_con, 
                    "select file_stream from files where file_id= %(id)s ", 
                    {'id':_r['file_id']})

        _temp = open(p_path + str(_e['file_id']) + '_' + _e['file_name'], 'rb')
        _temp.write(_w['file_stream'])
        _temp.flush()
        _temp.close
    return True


def upload_file(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, COOKIES={}, CONTEXT={}, TEMPLATE='', TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    CONTEXT.update({'PAGE_NAME':"Image Uploading"})
    _data = b''
    _fname = ''
    if len(POST)<1 :
        raise Exception('No Data in POST Object')
    if 'form_data' not in POST:
        raise Exception('POST Object is invalid missing information')
    
    _fd = POST.get('form_data')
    for _i in _fd:
        _h = _i.get('header')
    
        _r = write_file_to_db(p_con=ENVIRO.get('CONN'), 
                        p_user_id= int(ENVIRO.get('SEC',{}).get('USER_ID',-1)),
                        p_fname=_h.get('filename'),
                        p_type= _h.get('Content-Type'),
                        p_fstream=_i.get('data'))
    
    _fname = ENVIRO.get('IMAGES').get('filepath') + str(_r[0]['file_id']) + '_' + _h.get('filename')
    _freturn = ENVIRO.get('IMAGES').get('urlpath') + str(_r[0]['file_id']) + '_' + _h.get('filename')
    _f = open(_fname, 'wb')
    _f.write(_i.get('data'))
    _f.flush()
    _f.close()
    _output = '{"location": "/%s"}'%(_freturn)

    return True, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB
