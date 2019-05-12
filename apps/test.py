print('hellow world')

for i in range(1,101): 
    if i%3 == 0 and i%5 == 0:
        print('DirectEmployers')
    elif  i%3 == 0 :
        print('Direct')
    elif  i%5 == 0:
        print('Employers') 
    else: 
        print(i)


def reverse_string(_pstring='Hi There'):
    print(_pstring[::-1])

reverse_string()

def get_job_feed( purl= 'https://dejobs.org/jobs/feed/json?num_items=10'):
    from urllib import request as feed 
    import json
    _jay  = json.loads(feed.urlopen(purl).read().decode('utf-8'))
    _hold_string = ''
    _list= []
    for _url in _jay: 
        _t = 'url: ' + _url['url']
        _hold_string += _t + "\r\n" 
        _list.append(_t)
    
    print(_hold_string)
    return _list

    

get_job_feed()
