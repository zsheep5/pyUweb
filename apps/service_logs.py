import pyUwf as m 
from  urllib.parse import quote_plus as qp 

def list_services(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):

    q_str = """
    """
    message = GET.get('message',['-1'])[0]
    CONTEXT.update({'incidents': get_incident_hd(ENVIRO, -1) })
    CONTEXT.update({'PAGE_NAME':"List of Services" })
    CONTEXT.update({'PAGE_DESCRIPTION':"List of Open Services and Incidents"})
    CONTEXT.update({'app_messages':message})
    _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', ''))
    return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB

def get_incident(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    
    _key = int(GET.get('incdt_id', ['-1'])[0])
    _r = get_incident_hd(ENVIRO, _key)[0]
    CONTEXT.update({'incident': _r})

    CONTEXT.update({'todoitems':list_todoitem(ENVIRO, _key)})

    CONTEXT.update({'item_documents':get_linked_item_docs(ENVIRO,_r['item_id'])})
    CONTEXT.update({'wo_documents':get_linked_item_docs(ENVIRO,_r['wo_id'])})
    CONTEXT.update({'incident_documents':get_linked_item_docs(ENVIRO,_r['incdt_id'])})
    _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', ''))
    return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB

def save_incident(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    
    q_str = """Update incident set 
           incdt_descrip = %()s
        where incdt_id = %()s"""
    _incdt = m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':p_key})

    q_str = """update cntct set
            cntct_first_name = %()s,
            cntct_last_name = %()s , 
            cntct_phone = %()s,
            cntct_email = %()s
        where cntct_id = %()s"""
    _cntct = m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':p_key})

    q_str = """update addr set
            addr_line1 = %()s,
            addr_line2 =%()s ,
            addr_line3 = %()s,
            addr_city = %()s,
            addr_state = %()s 
        where addr_id = %()s"""

    _addr = m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':p_key})

    return m.client_redirect( ENVIRO, '/edit_incdt?message=', +qp('Failed to Create Quote Template'))

def list_todoitem(ENVIRO={}, p_key = -1):
    q_str = """ Select todoitem_id,
            todoitem_name, todoitem_description,
            todoitem_status, todoitem_active, 
            '<a href=view_todo?todo_id=' || todoitem_id::text || '>View </a>'as url_view_todo, 
            '<a href=close_todo?todo_id=' || todoitem_id::text || '>Close </a>'as url_close_todo,
            '<a href=del_todo?todo_id=' || todoitem_id::text || '>Delete</a>'as url_del_todo  

            from todoitem where todoitem_incdt_id = %(key)s """
    return m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':p_key})

def add_todoitem(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def close_todo(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def get_incident_hd(ENVIRO={}, p_key = -1):
    if p_key == -1:
        _where = "where incdt_incdtcat_id  = 4"
    else:
        _where = "where incdt_id = %s" % (p_key)
    q_str =""" select incdt_id, incdt_number, incdt_descrip,
                incdt_crmacct_id, cust_name, cust_number,
				incdt_summary,   incdt_link_type, incdt_link_id,
                incdt_descrip, incdt_item_id,  incdt_status
                incdt_ls_id, ls_number,
                item_number, item_descrip1, item_id,
                cntct_first_name, cntct_last_name,
                cntct_first_name || ' ' || cntct_last_name as contact,
                cntct_phone, cntct_email, cntct_notes,
                addr_id,
                addr_line1, addr_line2, addr_line3, addr_city,
                addr_state, addr_postalcode, addr_country,
                cntct_email, 
                wo_id,
                wo_number::text || '-' ||wo_subnumber::text as wo_number, 
                wodetails_shutdowncode, wodetails_serialnumber,  wo_prodnotes,
                '<a href=create_quote?incdt_id=' || incdt_id::text || '>Create Quote</a>'as url_create_quote,  
		        '<a href=get_incident?incdt_id=' || incdt_id::text || '>Edit</a>'as url_edit_incdt,
		        '<a href=get_map?addr_id=' || addr_id::text || '>Get Map</a>' as url_map,
                '<a href=edit_quote?quhead_id=' || incdt_link_id::text || '>Get Map</a>' as url_edit_qu
            from incdt
                left join cntct on incdt_cntct_id = cntct_id
                left join crmacct on crmacct_id = incdt_crmacct_id
                left join item on item_id = incdt_item_id
                left join ls on ls_id = incdt_ls_id
                left join addr on cntct_addr_id = addr_id
                left join wo on wo_id = ls_wo_id
                left join xmag.wodetails  on wodetails_wo_id = ls_wo_id
				left join custinfo on cust_id = crmacct_cust_id 
            %(_where)s 
            order by incdt_number desc
    """  % ({'_where':_where })

    return m.run_sql_command(ENVIRO.get('CONN'), q_str)

def get_link_wo_docs(ENVIRO= {}, pkey =-1):
    q_str = """select file_id, file_title,
        '<a href=get_file_from_xdb?file_id=' || file_id::text || '>'|| file_title ||'</a>'as url_dowload_file  
	            from file, docass
                where docass_source_id = %(key)s
                    and docass_source_type = 'WO'
                    and docass_target_id = file_id
                    and docass_target_type = 'FILE'; """ 
    return m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':pkey})

def get_linked_item_docs(ENVIRO= {}, pkey =-1):
    q_str = """select file_id, file_title,
        '<a href=get_file_from_xdb?file_id=' || file_id::text || '>'|| file_title ||'</a>'as url_dowload_file 
	            from file, docass
                where docass_source_id = %(key)s
                    and docass_source_type = 'I'
                    and docass_target_id = file_id
                    and docass_target_type= 'FILE'; """ 
    return m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':pkey})

def get_incdt_link_docs(ENVIRO= {}, pkey =-1):
    q_str = """select file_id, file_title,
'<a href=get_file_from_xdb?file_id=' || file_id::text || '>'|| file_title ||'</a>'as url_dowload_file 
	            from file, docass
                where docass_source_id = %(key)s
                    and docass_source_type = 'INCDT'
                    and docass_target_id = file_id
                    and docass_target_type = 'FILE'; """ 
    return m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':pkey})

def link_image(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def create_quote(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):

    _key = int(GET.get('incdt_id', ['-1'])[0])
    if _key < 0 :
        return m.client_redirect( ENVIRO, '/list_services', '303', CLIENT_STATE, COOKIES, CSB)

    q_str = """select xmag.create_quote_from_incident(%(key)s) as quhead_id """
    _r = m.run_sql_command(ENVIRO.get('CONN'), q_str, {'key':_key})

    if _r[0]['quhead_id'] > 1:
        return m.client_redirect( ENVIRO, '/edit_quote?quhead_id=' + _r[0]['quhead_id']
                                , '303', CLIENT_STATE, COOKIES, CSB)

    return m.client_redirect( ENVIRO, '/list_services?message=', +qp('Failed to Create Quote Template'),
    '303', CLIENT_STATE, COOKIES, CSB)

def edit_quote(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    
    _quhead = int(POST.get('quhead', ['-1'])[0])

    q_str = """Select quhead_id, quhead_custponumber, quhead_cust_id,
        quhead_ordercomments, quhead_shipcomments
        from quhead where quhead_id = %(_quhead_id)s

    """
    _header = m.run_sql_command(ENVIRO.get('CONN'), q_str, 
                {'_quhead_id':_quhead})
    
    CONTEXT.update({'quhead': _header[0]})

    q_str = """SELECT quitem_quhead_id , quitem_id, quitem_linenumber, quitem_itemsite_id, 
                    item_number,quitem_qtyord, quitem_qtyord * quitem_listprice as line_total,
                    quitem_price, quitem_custprice, stdCost(itemsite_item_id),
                    quitem_memo, quitem_listprice
                FROM quitem, itemsite, item
                where
                    quitem_itemsite_id = itemsite_id
                    and itemsite_item_id = item_id
                    and quitem_quhead= %(_quhead_id)s
                order by quitem_quhead_id desc,
                    quitem_linenumber"""
    _item = m.run_sql_command(ENVIRO.get('CONN'), q_str, 
                {'_quhead_id':_quhead})
    
    CONTEXT.update({'quitem': _item})

def save_quote(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    pass

def add_line_to_quote(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    
    _quhead = int(POST.get('quhead', ['-1'])[0])
    _qunumber = int(POST.get('qunumber', ['-1'])[0])
    _itemsite_id = int(POST.get('itemsite_id', ['-1'])[0])
    _qty = int(POST.get('qty', ['0'])[0])
    _warehouse = int(POST.get('warehouse', ['0'])[0])
    _message = 'Failed to Add Item the Quote'
    q_str = """select  xmag.additem_to_quote(
            %(quhead)s,
            %(itemsite_id)s,
            %(qty)s
            ) as idkey;
        """
    _r = m.run_sql_command(ENVIRO.get('CONN'), q_str, 
                {'itemsite_id': _itemsite_id,
                'quhead':_quhead,
                'qty':_qty
                })
    if _r[0]['idkey'] > 0:
        _message = 'Added the Item to the Quote'
    _redirect = """ /list_van_inventory?message=%s;warehouse=%s;qunumber=%s;quhead=%s""" %(_message,_warehouse,_qunumber, _quhead)
    return m.client_redirect( ENVIRO, _redirect,'303', CLIENT_STATE, COOKIES, CSB)

def list_van_inventory(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    
    _pkey = int(GET.get('warehouse', ['-1'])[0])
    _quhead = int(GET.get('quhead_id', ['-1'])[0])
    _qunumber = GET.get('qunumber', ['ERROR'])[0]

    q_str = """ select item_number, item_descrip1, item_listprice, 
               itemsite_id, itemsite_qtyonhand, itemsite_warehous_id,
               %(quhead_id)s as quhead
            from item 
            left join itemsite on itemsite_item_id = item_id
            where itemsite_warehous_id = %(pkey)s
            order by 1 desc"""

    _r = m.run_sql_command(ENVIRO.get('CONN'), q_str, 
                {'pkey': _pkey,
                'quhead_id':_quhead
                })
    CONTEXT.update({'van_inventory':_r})
    CONTEXT.update({'quote_number':_qunumber})
    _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', ''))
    return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB

def add_additem_to_quote(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, 
                COOKIES={}, CONTEXT={}, TEMPLATE='', 
                TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):

    pass     




