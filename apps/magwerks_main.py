def start(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
        COOKIES={}, CONTEXT={}, TEMPLATE='', 
        TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}): 
    _key = -1
    CONTEXT.update({'PAGE_NAME':"Service  and Customer Portal"})
    CONTEXT.update({'PAGE_DESCRIPTION':"Magwerks Service, Calibration and Customer Portal"})
    
    _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', ''))
    return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB
