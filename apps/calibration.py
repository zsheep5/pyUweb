import pyUwf as m

def list_certs(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):

    q_str = """
    select calhead_id as id, calhead_id, calhead_coitem_id, cust_name,
        calprohd_descrip, calprohd_report_id, 
		calhead_caldate, calhead_expire, calhead_status, 
		(select caldetail_default_text 
            from mcal.caldetail 
		    where caldetail_descrip_text_datacollect = 'Serial Number' 
                and caldetail_calhead_id = calhead_id
        ) as serial 
		from mcal.calhead 
		left join mcal.calprohd on calhead_calprohd_id = calprohd_id 
		left join custinfo on calhead_cust_id = cust_id 
		order by calhead_caldate"""
    CONTEXT.update({'cal_head': m.run_sql_command(ENVIRO.get('CONN'), q_str)})
    CONTEXT.update({'cert_types':get_cert_types(ENVIRO)})
    
    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str)
    _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', ''))
    return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB

def get_cert_types(ENVIRO= {}):
    q_str =  """select json_agg( 
                    json_build_object( 
                        trim( both  from calprohd_descrip, ' ' ) ,
                        calprohd_id 
                    ) ) as cert_types
                    from (
                    select distinct calprohd_descrip,
                            calprohd_id 
                        from mcal.calprohd 
                        where calprohd_expire > now()::Date 
                        order by 1 ) ct"""
    import html_helpers as hh
    _r = m.run_sql_command(ENVIRO.get('CONN'),q_str ) 
    _r = hh.html_combobox( _r[0]['cert_types'])

    return  _r

def get_item_linked_to_certs(ENVIRO={}, pcalprohd_id=-1):
        
    q_str = """ 
        select json_agg( 
            json_build_object(
                trim( both from item_descrip1, ' ' ) ,
                item_id 
                ) ) as item_linked
            from ( select  item_id, item_descrip1  
	                from mcal.calpro_item_link, item
	                where calpil_item_id = item_id
	                and calpil_calprohd_id = %(calprohd_id)s
                )"""

    import html_helpers as hh
    _r = m.run_sql_command(ENVIRO.get('CONN'), q_str, 
                            {'calprohd_id':pcalprohd_id})
    _r = hh.html_combobox( _r[0]['item_linked'])    

    return _r 
    
def get_cert_statuses():
    import html_helpers as hh
    cert_status = {
                    "Open":"0", 
                    "In Process":"1", 
                    "Needs Repair":"2",
                    "Passed":"3", 
                    "Passed with Recalibration":"4", 
                    "Failed":"5", 
                    "Canceled":"6", 
                    "Limited":"7" 
                    }
    _r = hh.html_combobox_from_dic( dd )

    return  _r

def save_cert_header(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def save_cert_detail(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def enter_cert_detail(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def email_cert(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def get_cert_headers(ENVIRO={}, pwhere='', poffset=-1, plimit=25, orderby='cert_id' ):
    _sql = """select calhead_id, 
                    calhead_calprohd_id ,
                    calhead_cust_id ,
                    calhead_cntct_id ,
                    calhead_caldate ,
                    calhead_expire ,
                    calhead_temp ,
                    calhead_humdity ,
                    calhead_operator_notes ,
                    calhead_coitem_id ,
                    calhead_failcert ,
                    calhead_status ,
                    calhead_addr_line1 ,
                    calhead_addr_line2 ,
                    calhead_addr_line3 ,
                    calhead_addr_city ,
                    calhead_addr_state ,
                    calhead_addr_postalcode ,
                    calhead_addr_country ,
                    calhead_addr_number,
                    calhead_cntct_name ,
                    calhead_cntct_phone ,
                    calhead_cntct_fax ,
                    calhead_cntct_email ,
                    calhead_cntct_title ,
                    calhead_eqname ,
                    calhead_notesprinted ,
                    calhead_operator ,
                    calhead_supersedes ,
                    calhead_cust_po 
                from mcal.calhead 
                where %(pwhere)s  >= %(poffset)s
                order by %(orderby)s  
                limit %(plimit)s """

    if orderby != 'cert_id':
        poffset = ''

    return m.run_sql_command(ENVIRO.get('CONN'), _sql, 
                    {'pwhere':pwhere,
                    'poffset':poffset,
                    'orderby':orderby,
                    'plimit':plimit,
                    }
                )

def get_cert_detail(ENVIRO={}, pcert_id=-1):

    _where = ''
    _sql = """ select caldetail_id,
                        caldetail_calhead_id,
                        caldetail_calprorules_id ,
						caldetails_seqence ,
						caldetail_std_asrcv ,
						caldetail_mut_asrcv ,
						caldetail_std_afterrcv ,
						caldetail_mut_afterrcv ,
						caldetail_timestamp ,
						caldetail_datatype ,
						caldetail_descrip_text_datacollect ,
						caldetail_default_text ,
						caldetail_checkoff_descrip ,
						caldetail_checkoff_values ,
						caldetail_dev_asrcv_low ,
						caldetail_checkoff_flag ,
						caldetail_dev_afterrcv_low ,
						caldetail_dev_asrcv_high ,
						caldetail_dev_afterrcv_high ,
						caldetail_devtext ,
						caldetail_standard_altvalue,
						caldetail_checkoff_na
                from mcal.caldetail  """
    if cert_id > -1 :
        _where=" where caldetail_calhead_id = %(cert_id) " 
        _sql = _sql + _where
    _sql = _sql + " order by caldetails_seqence "
    
    return m.run_sql_command(ENVIRO.get('CONN'), _sql, {'cert_id':pcert_id})

def get_cert_report(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    
    if 'calhead_id' in GET:
        _key = int(''.join(GET.get('calhead_id','-1')))
    elif 'calhead_id' in POST:
        _key = int(''.join(POST.get('calhead_id','-1')))
    
    if _key == -1:
        return True, '', ENVIRO, CLIENT_STATE, COOKIES, CSB 
    
    CONTEXT.update({'PAGE_NAME':"Cert Report for "})
    q_str = """select xmag.xtuple_report_to_pdf(
	                calprohd_report_id,
	                array['calhead_id=' || calhead_id::text],
	                true) as report_binary,
                    'Certificate_' || calhead_id || '.pdf' as report_name
                from mcal.calprohd, mcal.calhead
	            where calprohd_id = calhead_calprohd_id 
                    and calhead_id = %(calhead_id)s
             """
    _r = m.run_sql_command(ENVIRO.get('CONN'),q_str, {'calhead_id':_key})
    ENVIRO.get('HEADERS',{}).update(
        {'Content-Type': 'application/pdf', 
        'Content-Description':_r.['report_name'],
        'Content-Disposition':'attachment; filename="%s"'%(_r.['report_name'])
        })

    return True, _r[0].['report_binary'], ENVIRO, CLIENT_STATE, COOKIES, CSB 
