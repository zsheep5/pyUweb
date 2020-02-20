import session_controller as sc
import pyUwf as m
import psycopg2, psycopg2.extras 
from html2text import html2text as extext
from  urllib.parse import quote_plus as qp 


## the view mode of the family blog.   
## lets get the last 15 items from the database as the default
def view(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, COOKIES={}, CONTEXT={}, TEMPLATE='', TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}): 
    _key = -1
    CONTEXT.update({'PAGE_NAME':"zSheep's Blog"})
    if 'blog_id' in GET:
        _key = int(''.join(GET.get('blog_id','-1')))
    elif 'blog_id' in POST:
        _key = int(''.join(POST.get('blog_id','-1')))
    _results, CONTEXT = get_blog_by_id(_key, CONTEXT, ENVIRO)
    if _results :
        if _key == -1 :
            _blog = CONTEXT.get('blog', {})
            _key = _blog.get('blog_id',-1)
        _r, CONTEXT = get_comments(_key, CONTEXT=CONTEXT, ENVIRO=ENVIRO)
        _r, CONTEXT = get_blog_counts(_key, CONTEXT=CONTEXT, ENVIRO=ENVIRO)
        _r, CONTEXT = get_top_post(CONTEXT=CONTEXT, ENVIRO=ENVIRO)
        _r, CONTEXT = get_newer_post(_key, CONTEXT,ENVIRO)
        _r, CONTEXT = get_older_post(_key, CONTEXT,ENVIRO)

        _r, CONTEXT = get_cats( m.check_dict_for_list(POST),  
                                m.check_dict_for_list(GET), 
                                ENVIRO, CLIENT_STATE, 
                                COOKIES, CONTEXT, 
                                TEMPLATE, TEMPLATE_ENGINE)
        _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', ''))
        return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB
    return False, ''

def search_blog(POST={}, GET={}, ENVIRO={}, CLIENT_STATE={}, COOKIES={}, CONTEXT={}, TEMPLATE='', TEMPLATE_ENGINE=None, CSB='', TEMPLATE_STACK={}):
    _text = ''
    CONTEXT.update({'PAGE_NAME':"Searching Through the Blog"})
    if 'search_value' in POST:
        _text = POST['search_value']
    elif 'search_value' in GET:
        _text = GET['search_value']
    else:
        CONTEXT.update({'search_count':'0'})
        return True
    
    q_str = """select blog_id, blog_title, blog_date, 
                blog_htmltext,
                ts_rank_cd(blog_tsv, query) AS rank
            from blog,  to_tsquery('english', %(search_value)s)  query
            where 
                blog_tsv @@ query
            order by rank desc
                """
    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str, { 'search_value':_text })
    if len(_rec) > 0:
        _cat = []
        for _r in _rec:
            _cat.append({'blog_url': 
                        build_get_url('view',
                                {'blogkey':_r.get('blog_id')}
                            ),
                        'blog_title':_r.get('blog_title',''),
                        'blog_date': _r.get('blog_date',''),
                        'blog_text_250':html2text(_r.get('blog_htmltext','')[0:250]),
                        'rank':_r.get('rank','0')
                    }
                )
        CONTEXT.update({'search_results':_rec[0]})
        _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE,
                            ptype = 'string', 
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_TMP_PATH'))
        return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB

    return False

def get_blog_by_id(pid=-1, CONTEXT={}, ENVIRO={}):  ##should always return  record set in the form list of list 
    q_str = """select blog_id, blog_user_id,  blog_title, blog_date::date as blog_date, 
                blog_htmltext, array_to_string(search_tags, '<br>') as search_tags, 
                search_tags as list_tags
        from blog  """
    if pid < 0: 
        q_str += """ order by blog_date desc """
    else :
        q_str += """ where blog_id = %(blogid)s""" 
    _rec  = m.run_sql_command(ENVIRO.get('CONN'),q_str, { 'blogid':pid } )
    if len(_rec) > 0:
        _rec[0]['list_tags'] =  m.db_arrary_tolist_dic(_rec[0]['list_tags'], 'list_tags')
        CONTEXT.update({'blog':_rec[0]})
        return True, CONTEXT 

    return False, CONTEXT

def delete(ids=[]): ##past a list of the primary IDs to delete.
    return True

def get_blogs_list(search_by, offset=0, limit=25):
    pass

def build_pager():
    pass

def get_more_results(p_id=-1, p_offset=0, p_limit=50):
    pass 

def get_comments(p_id=-1, p_offset=0, p_limit=50, CONTEXT={}, ENVIRO={}):
    q_str = """ select bc_id , bc_blog_id , bc_parent_bc_id, bc_user_id,
	            bc_date, bc_comment, bc_title, user_displayname, user_avatar,
                (select count(bc_parent_bc_id) from blog_comments dd where dd.bc_id = bc_id) as bc_child_count 
                from  blog_comments, users where
                bc_blog_id  = %(blogid)s 
                and bc_user_id = user_id 
                limit %(p_limit)s  offset %(p_offset)s 
                """
    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str, { 'blogid':p_id, 'p_limit': p_limit, 'p_offset': p_offset } )
    if len(_rec) > 0:
        CONTEXT.update({'comments':_rec})
        return True, CONTEXT
    return False, CONTEXT

def get_child_comments(POST, GET, ENVIRO, CLIENT_STATE, COOKIES, CONTEXT, TEMPLATE, TEMPLATE_ENGINE, CSB='', TEMPLATE_STACK={}):
    if 'bc_id' in GET and 'limit' in GET and 'offset' in GET:

        q_str = """ select bc_id , bc_blog_id , bc_parent_bc_id,
                    bc_user_id,	bc_date, bc_comment, bc_title,
                    (select count(bc_parent_bc_id) from blog_comments dd where dd.bc_id = bc_id) as bc_child_count 
                    from  blog_comments where
                    bc_id  = %(bc_id)s 
                    limit %(limit)s  offset %(offset)s """
        _rec = m.run_sql_command(ENVIRO.get('CONN'),q_str, { 'bc_id':g.GET.get(bc_id, 0), 
                            'p_limit': g.GET.get('limit', 0), 
                            'p_offset': p_offset.get('offset',50) } )
        _rec = cur.fetchall()
        if len(_rec) > 0:   
            CONTEXT.update({'child_comments':_rec})
            _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type = 'string' 
                            )
            return True, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB 

    return False, '', ENVIRO, CLIENT_STATE, COOKIES, CSB

def add_comment(p_id=-1, p_user_id=-1, p_text='', p_bc_parent=None,):
    q_str = """ insert into blog_comments values ( default, %(blog_id),
               %(bc_user_id)s, now(), %(bc_comment)s,  
               %(bc_comments)s::tsvector  ) """
    _topass = {'blog_id': p_id, 'bc_user_id':p_user_id,
                'bc_comment': p_text}
    return m.run_sql_command(ENVIRO.get('CONN'),q_str, _topass)

def edit_blog(POST, GET, ENVIRO, CLIENT_STATE, COOKIES, CONTEXT, TEMPLATE, TEMPLATE_ENGINE, CSB='', TEMPLATE_STACK={}):
    CONTEXT.update({'PAGE_NAME':"Editing blogs"})
    if not m.check_credentials('blog.edit_blog', SEC.get('USER_ID',-1) ):
        return m.log_in_page()

    if 'blog_id' in GET:
        _key = int(g.GET['blog_id'])
    elif 'blog_id' in POST:
        _key = int(Post['blog_id'])

    if _key == -1:
        return False

    _sql = "select blog_title, blog_htmltext from blog where blog_id = %(blog_id)s;"

    _rec = m.run_sql_command(ENVIRO.get('CONN'),_sql, {'blog_id':_key})
    if len(_rec) == 0 :
        return False, '', ENVIRO, CLIENT_STATE, COOKIES, CSB 
    CONTEXT.update({'submit_command':'save_blog',
                      'blog_id':_key, 
                      'title': _rec.get('blog_title',''),
                      'content':_rec.get('blog_html','')
                    })
    _ouput = TEMPLATE_ENGINE(pfile =TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type = 'string')
    return True, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB 

def new_blog(POST, GET, ENVIRO, CLIENT_STATE, COOKIES, CONTEXT, TEMPLATE, TEMPLATE_ENGINE, CSB='', TEMPLATE_STACK={}):
    cc = {'blog_id' : m.get_db_next_id(ENVIRO.get('CONN'),"blog_blog_id_seq"),
    'submit_command': 'save_blog',
    'blog_title': 'Blog Title',
    'search_tags':'Meta and Search Tag here',
    'PAGE_NAME': 'Create a New Blog.'
    }
    import html_helpers as hh
    _r = m.run_sql_command(ENVIRO.get('CONN'),
                            """select json_agg( 
                                    json_build_object( 
                                        trim( both  from cat_short, ' ' ) ,
                                        cat_id 
                                    ) ) as cat
		                            from category  """
                        ) 
    _r = hh.html_combobox( _r[0]['cat'])

    CONTEXT.update({'category_combo':_r})
    CONTEXT.update(cc)
    _r, CONTEXT = get_cats(POST, GET, ENVIRO, CLIENT_STATE, COOKIES, CONTEXT, TEMPLATE, TEMPLATE_ENGINE, CSB, TEMPLATE_STACK)

    _output = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type = 'string' 
                            )
    return True, _output, ENVIRO, CLIENT_STATE, COOKIES, CSB 

def save_blog(POST, GET, ENVIRO, CLIENT_STATE, COOKIES, CONTEXT, TEMPLATE, TEMPLATE_ENGINE, CSB='', TEMPLATE_STACK={}):
    if 'blog_id' in GET :
        _key = int(''.join(GET.get('blog_id')),'-1')
        _search_tags = ''.join(GET.get('search_tags', '')).split(',')
        _text = ''.join(GET.get('content', ''))
        _title = ''.join(GET.get('title', ''))
    elif 'blog_id' in POST:
        _key = int(''.join(POST.get('blog_id','-1')))
        _search_tags = ''.join(POST.get('search_tags', '')).split(',')
        _text = ''.join(POST.get('content', ''))
        _title = ''.join(POST.get('title', ''))
    else  :
        return False, '', ENVIRO, CLIENT_STATE, COOKIES, CSB
    CONTEXT.update({'PAGE_NAME':"New Blog Was Saved"})
    _sql = """ insert into blog values (
            %(blog_id)s ,
            %(blog_user_id)s ,
            now(),
            %(blog_htmltext)s ,
            %(search_tags)s ,
            to_tsvector(%(tvs)s),
            %(blog_title)s )
        on Conflict ( blog_id ) do Update set  
            blog_htmltext =   %(blog_htmltext)s ,
            search_tags = %(search_tags)s,
            tvs = to_tsvector(%(tvs)s),
            blog_title =%(blog_title)s ;"""

    _topadd = { 'blog_id': _key,
            'blog_user_id':int(ENVIRO.get('SEC',{}).get('USER_ID',-1)),
            'blog_htmltext': _text,
            'search_tags': _search_tags,
            'tvs': _title + extext(_text),
            'blog_title': _title

    }
    m.run_sql_command(ENVIRO.get('CONN'),_sql, _topadd)
    #GET = {'blogkey':_key}
    #_is_in_cache, TEMPLATE, _template_name = m.build_template('view', TEMPLATE_STACK['view'], ENVIRO=ENVIRO)
    #return view({}, GET, ENVIRO, CLIENT_STATE, COOKIES, CONTEXT,TEMPLATE, TEMPLATE_ENGINE, '', TEMPLATE_STACK )
    _r, url_path =m.furl_get_to_app('view', ENVIRO, {'blog_id':_key})
    if _r :
        ENVIRO= m.client_redirect(url_path, ENVIRO)
    return True, '', ENVIRO, CLIENT_STATE, COOKIES, CSB

def comment_on_blog(POST, GET, ENVIRO, CLIENT_STATE, COOKIES, CONTEXT, TEMPLATE, TEMPLATE_ENGINE,CSB='', TEMPLATE_STACK={} ):
    if 'blog_id' in GET :
        _key = int(''.join(GET.get('blog_id')),'-1')
        _search_tags = ''.join(GET.get('search_tags', '')).split(',')
        _text = ''.join(GET.get('content', ''))
        _title = ''.join(GET.get('title', ''))
    elif 'blog_id' in POST:
        _key = int(''.join(POST.get('blog_id','-1')))
        _search_tags = ''.join(POST.get('search_tags', '')).split(',')
        _text = ''.join(POST.get('content', ''))
        _title = ''.join(POST.get('title', ''))
    else  :
        return False, '', ENVIRO, CLIENT_STATE, COOKIES, CSB
    q_str =  """ insert into values
            (
                default, %(blog_user_id)s, now() ,
                %(blog_htmltext)s, %(search_tags)s , 
                %(tvs)s::tsvector , %(blog_title)s
            ) returning blog_id as id
    """
    _topass = {'blog_user_id':p_user , 'blog_htmltext':p_htmltext, 
                'search_tags':p_tags ,  
                'tvs': p_tags + '' + p_title + '' + extext(p_htmltext),
                'blog_title':p_title 
            }
    _rec = m.run_sql_command(q_str, _topass)

    if len(_rec)>0:
        POST.update({'blogkey':_rec[0]['blog_id']})
        _is_in_cache, TEMPLATE, _template_name = m.build_template(papp_command, get_template_stack('view'), True)
        return view(POST, GET, ENVIRO, CLIENT_STATE, COOKIES, {},TEMPLATE, TEMPLATE_ENGINE )

def get_cats(POST, GET, ENVIRO, COOKIES, CLIENT_STATE, CONTEXT, TEMPLATE, TEMPLATE_ENGINE, CSB='', TEMPLATE_STACK={}):
    q_str= """ select  '?cat_id=' || cat_id::text as url, cat_short as Name, 
                cat_long || ' ' ||  coalesce(bc_count, 0)::text as LinkText
            from category 
                left join ( select count(*) as bc_count, 
                                bc_cat_id from blog_cats 
                                group by bc_cat_id ) bl
                    on bc_cat_id = cat_id 
    """

    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str)
    _cat = m.build_url_links( _rec, p_url_path='', p_app_command='view_category', ENVIRO=ENVIRO)
    CONTEXT.update({'category':_cat})
    return True, CONTEXT

def list_category(  POST, GET, ENVIRO, COOKIES, CLIENT_STATE, CONTEXT, TEMPLATE, TEMPLATE_ENGINE, CSB='', TEMPLATE_STACK={}):
    _key = -1
    if 'cat_id' in GET:
        _key = int(''.join(GET.get('cat_id','-1')))
        _prev_id = int(''.join(GET.get('prev_id','9999999999')))
        _count = int(''.join(GET.get('count','-1')))
    elif 'cat_id' in POST:
        _key = int(''.join(POST.get('cat_id','-1')))
        _prev_id = int(''.join(POST.get('prev_id','9999999999')))
        _count = int(''.join(POST.get('count','-1')))

    q_str= """ select  '?blog_id=' || blog_id::text as url, blog_title as Name, 
                Blog_title  as LinkText
            from blog, blog_cats 
                where bc_blog_id = blog_id 
                    and bc_cat_id = %(cat_id)s
                    and blog_id <= %(prev_id)s
                    ordered by blog_id desc 
                    limit by %(count)s)
    """
    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str, {'cat_id': _key, 'prev_id':_prev_id, 'count':_count})
    _list_arts = m.build_url_links( _rec, p_url_path='', p_app_command='view_category', ENVIRO=ENVIRO)
    CONTEXT.update({'list_articles':_list_arts})
    _rec = m.run_sql_command(ENVIRO.get('CONN'), 
                    "select cat_long from catergory where cat_id = %(cat_id)", 
                    {'cat_id': _key,})
    CONTEXT.update({'PAGE_NAME':"List of Blogs in "+ _rec[0]['cat_long']})

    _ouput = TEMPLATE_ENGINE(pfile = TEMPLATE, 
                            ptype = 'string',
                            pcontext = CONTEXT, 
                            preturn_type ='string', 
                            pcache_path = ENVIRO.get('TEMPLATE_CACHE_PATH_PRE_RENDER', ''))

    return True, _ouput, ENVIRO, CLIENT_STATE, COOKIES, CSB

def get_top_post( CONTEXT={},ENVIRO={}):

    q_str = """select '?id=' ||  blog_id::text as url, blog_title as Name, 
            blog_title || ' ' ||  coalesce(bc_views, 0)::text as LinkText
            from blog, blog_counter where
            blog_id = bc_blog_id 
            order by bc_views desc
            limit 5 
    """

    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str)
    _tops = m.build_url_links( _rec, p_url_path='', p_app_command='view', p_escape=False, ENVIRO=ENVIRO)
    CONTEXT.update({'tops':_tops})
    return True, CONTEXT

def get_blog_counts(p_id, CONTEXT={}, ENVIRO={}):
    q_str = """ select bc_views 
                from blog_counter where bc_blog_id = %(id)s  """

    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str, {'id': p_id})
    CONTEXT.update({'web_urls':  m.build_url_links(_rec, ENVIRO=ENVIRO)}) 
    return True, CONTEXT

def get_blog_view_counts(p_id, CONTEXT= {}, ENVIRO={}):
    q_str = """ select blog_title as Name, 
                        blog_title || coalesce(bc_views, 0)::text as LinkText,
                        '?id='||blog_id::text as url
                from blog 
                    left join blog_counter on blog_id = bc_blog_id
                order by blog_counter desc limit 5  """
    
    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str)
    CONTEXT.update({'web_urls':  m.build_url_links(_rec, ENVIRO=ENVIRO)}) 
    return True, CONTEXT 

def up_blog_view_count(p_id=-1):
    if p_id < 0:
        return True
    q_str = """ insert into blog_counter values
        ( %(p_id)s, 1 ) 
        on conflict  blog_counter_pkey 
        do update set bc_views = (bc_views+1) where
        bc_blog_id =  %(p_id)s"""
    _topass = { 'p_id': p_id}
    con = g.CONN['PG1'] 
    cur = con.cursor()
    cur.execute(q_str, _topass)
    return True

def update_blog():
    pass

def delete_comment():
    pass

def get_newer_post(p_id, CONTEXT={},ENVIRO={}):
    q_str = """select '?blog_id=' ||  blog_id::text as url, blog_title as Name, 
            blog_title as LinkText
            from blog where
            blog_id > %(p_id)s order by 1 asc limit 1 ;

    """
    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str,  {'p_id':p_id})
    if len(_rec) ==1: 
        _tops = m.build_url_links( _rec, p_url_path='', p_app_command='view', p_escape=False, ENVIRO=ENVIRO)
        CONTEXT.update({'newer':_tops[0]})
    else :
        CONTEXT.update({'newer':'no newer posts'})
    return True, CONTEXT

def get_older_post(p_id, CONTEXT={},ENVIRO={}):
    q_str = """select '?blog_id=' ||  blog_id::text as url, blog_title as Name, 
            blog_title as LinkText
            from blog where
            blog_id < %(p_id)s order by 1 desc limit 1 ;

    """
    _rec = m.run_sql_command(ENVIRO.get('CONN'), q_str, {'p_id':p_id})
    if len(_rec) ==1: 
        _tops = m.build_url_links( _rec, p_url_path='', p_app_command='view', p_escape=False, ENVIRO=ENVIRO)
        CONTEXT.update({'older':_tops[0]})
    else :
        CONTEXT.update({'older':'no older posts'})
    return True, CONTEXT