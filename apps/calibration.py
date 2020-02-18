import pyUwf as m

def list_cal(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
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
        ) as serial,
        '<a href=cert_edit?calhead_id=' || calhead_id::text || '>Edit Cert</a>'as url_edit,  
		'<a href=cert_report?calhead_id=' || calhead_id::text || '>Report</a>'as url_report,
		'<a href=cert_replace?calhead_id=' || calhead_id::text || '>Replace</a>' as url_replace
		from mcal.calhead 
		left join mcal.calprohd on calhead_calprohd_id = calprohd_id 
		left join custinfo on calhead_cust_id = cust_id 
		order by calhead_caldate"""
    
    CONTEXT.update({'cal_head': m.run_sql_command(ENVIRO.get('CONN'), q_str)})
    CONTEXT.update({'cert_types':get_cert_types(ENVIRO)})
    CONTEXT.update({'PAGE_NAME':"List Certificates" })
    CONTEXT.update({'PAGE_DESCRIPTION':"Page listing certificates to edit, print and replace"})
    
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

def get_cert_edit(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    
    
    if 'calhead_id' in GET:
        _key = int(''.join(GET.get('calhead_id','-1')))
    elif 'calhead_id' in POST:
        _key = int(''.join(POST.get('calhead_id','-1')))
    
    if _key == -1:
        return True, '', ENVIRO, CLIENT_STATE, COOKIES, CSB 
    CONTEXT.update({'calhead': get_cert_header(ENVIRO, _key)[0]})
    CONTEXT.update({'caldetail':get_cert_detail_edit(ENVIRO, _key)})
    CONTEXT.update({'PAGE_NAME':"Edit Certificate" + str(_key)})
    CONTEXT.update({'PAGE_DESCRIPTION':"Editing calibration certificates"})

    _output = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type = 'string' 
                            )

    return True, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB
def cert_replace(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass
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
def submit_cal_save(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    if 'calhead_id' in GET:
        _key = int(''.join(GET.get('calhead_id','-1')))
    elif 'calhead_id' in POST:
        _key = int(''.join(POST.get('calhead_id','-1')))
    
    if _key == -1:
        return True, '', ENVIRO, CLIENT_STATE, COOKIES, CSB 

def submit_cal_copy(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
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

def get_cert_header_page(ENVIRO={}, pwhere='', poffset=-1, plimit=25, orderby='cert_id' ):
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

def get_cert_header(ENVIRO={}, pcalhead_id=-1 ):
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
                where calhead_id = %(pcalhead_id)s  
                """
    return m.run_sql_command(ENVIRO.get('CONN'), _sql, 
                    {'pcalhead_id':pcalhead_id}
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

def get_cert_detail_edit(ENVIRO={}, pcert_id=-1):
    _sql =  """select calprorange_description, calprorules_desired_value,
            caldetail_id,
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
						caldetail_default_text as caldetail_text ,
						caldetail_checkoff_descrip ,
						caldetail_checkoff_values ,
						caldetail_dev_asrcv_low ,
						caldetail_checkoff_flag ,
						caldetail_dev_afterrcv_low ,
						caldetail_dev_asrcv_high ,
						caldetail_dev_afterrcv_high ,
						caldetail_devtext ,
						caldetail_standard_altvalue,
						caldetail_checkoff_na, 
            lag(caldetail_datatype) OVER (order by caldetails_seqence asc) as prev_datatype, 
            calprorules_id, calprorules_calprorange_id, 
            lag(calprorules_calprorange_id) OVER (order by caldetails_seqence asc) as prev_rangeid, 
            calprorules_standard_altvalue, 
            lag(calprorules_standard_altvalue) OVER (order by caldetails_seqence asc) as prev_altvalue, 
            unit.unit_shortdescr, stdunit.unit_shortdescr as stdunitshortdesc 
		from mcal.caldetail 
            left join mcal.calprorules on caldetail_calprorules_id = calprorules_id 
            left join mcal.calprorange on calprorange_id = calprorules_calprorange_id 
            left join mcal.unit on calprorange_unit_id = unit_id 
            left join mcal.calstandards on calprorules_id = calstd_calprorules_id 
            left join mcal.equip_range on calstd_equip_id = range_equip_id 
            left join mcal.unit stdunit on range_unit = stdunit.unit_id 
		where caldetail_calhead_id = %(cert_id)s 
		    and caldetail_calprorules_id = calprorules_id 
		order by caldetails_seqence asc;"""
    
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
        'Content-Description':_r[0]['report_name'],
        'Content-Disposition':'attachment; filename="%s"'%(_r[0]['report_name'])
        })

    return True, _r[0]['report_binary'], ENVIRO, CLIENT_STATE, COOKIES, CSB 
