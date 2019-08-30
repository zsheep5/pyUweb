import globals as g
import pyUwf as m
import psycopg2, psycopg2.extras 
from html2text import html2text as extext
from  urllib.parse import quote_plus as qp 


def execute():
    ## first step is figure out what we are doing
    ## lets take a look if we have POST or GET events
    if g.GET =={} and g.POST=={}: ## if both are empty ODD nothing to do
        return False # should always test to make we get what we expect
    if g.GET['QUERY_STRING_COUNT'] > 0: #means no query was sent typical default view
        GET(g.GET)
    elif g.POST['POST_COUNT'] > 0 :
        POST(g.POST)
    return True

## the view mode of the family blog.   
## lets get the last 15 items from the database as the default
def view(): 
    _key = -1
    if 'blogkey' in g.GET:
            _key = int(g.GET.get('blogkey',-1))
    elif 'blogkey' in g.POST:
           _key = int(g.POST.get('blogkey',-1))
    if get_blog_by_id(_key):
        if _key == -1 :
            _blog = g.CONTEXT.get('blog', {})
            _key = _blog.get('blog_id',-1)
        get_comments(_key)
        get_blog_counts(_key)
        get_cats()
        return True
    return False

def search_blog():
    _text = ''
    if 'search_value' in g.POST:
        _text = g.POST['search_value']
    elif 'search_value' in g.GET:
        _text = g.GET['search_value']
    else:
        g.CONTEXT.update({'search_count':'0'})
        return True
    
    q_str = """select blog_id, blog_title, blog_date, 
                blog_htmltext,
                ts_rank_cd(blog_tsv, query) AS rank
            from blog,  to_tsquery('english', %(search_value)s)  query
            where 
                blog_tsv @@ query
            order by rank desc
                """
    _rec = m.run_sql_command(q_str, { 'search_value':_text })
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
        g.CONTEXT.update({'search_results':_rec[0]})
        return True

    return False

def get_blog_by_id(pid=-1):  ##should always return  record set in the form list of list 
    q_str = """select blog_id, blog_user_id,  blog_title, blog_date, 
                blog_htmltext, array_to_string(search_tags, '<br>') as search_tags 
        from blog  """
    if pid < 0: 
        q_str += """ order by blog_date desc """
    else :
        q_str += """ where blog_id = %(blogid)s""" 
    _rec  = m.run_sql_command(q_str, { 'blogid':pid } )
    if len(_rec) > 0:
        g.CONTEXT.update({'blog':_rec[0]})
        return True

    return False

def delete(ids=[]): ##past a list of the primary IDs to delete.
    return True

def get_blogs_list(search_by, offset=0, limit=25):
    pass

def build_pager():
    pass

def get_more_results(p_id=-1, p_offset=0, p_limit=50):
    pass 

def get_comments(p_id=-1, p_offset=0, p_limit=50):
    q_str = """ select bc_id , bc_blog_id , bc_parent_bc_id, bc_user_id,
	            bc_date, bc_comment, bc_title, user_displayname, user_avatar,
                (select count(bc_parent_bc_id) from blog_comments dd where dd.bc_id = bc_id) as bc_child_count 
                from  blog_comments, users where
                bc_blog_id  = %(blogid)s 
                and bc_user_id = user_id 
                limit %(p_limit)s  offset %(p_offset)s 
                """
    con = g.CONN['PG1'] 
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q_str, { 'blogid':p_id, 'p_limit': p_limit, 'p_offset': p_offset } )
    _rec = cur.fetchall()
    if len(_rec) > 0:
        g.CONTEXT.update({'comments':_rec})
        return True
    return False

def get_child_comments():
    if 'bc_id' in g.GET and 'limit' in g.GET and 'offset' in g.GET:

        q_str = """ select bc_id , bc_blog_id , bc_parent_bc_id,
                    bc_user_id,	bc_date, bc_comment, bc_title,
                    (select count(bc_parent_bc_id) from blog_comments dd where dd.bc_id = bc_id) as bc_child_count 
                    from  blog_comments where
                    bc_id  = %(bc_id)s 
                    limit %(limit)s  offset %(offset)s """
        con = g.CONN['PG1'] 
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(q_str, { 'bc_id':g.GET.get(bc_id, 0), 
                            'p_limit': g.GET.get('limit', 0), 
                            'p_offset': p_offset.get('offset',50) } )
        _rec = cur.fetchall()
        if len(_rec) > 0:   
            g.CONTEXT.update({'child_comments':_rec})
            return True
    return False

def add_comment(p_id=-1, p_user_id=-1, p_text='', p_bc_parent=None,):
    q_str = """ insert into blog_comments values ( default, %(blog_id),
               %(bc_user_id)s, now(), %(bc_comment)s,  
               %(bc_comments)s::tsvector  ) """
    _topass = {'blog_id': p_id, 'bc_user_id':p_user_id,
                'bc_comment': p_text}
    con = g.CONN['PG1'] 
    cur = con.cursor()
    cur.execute(q_str, _topass)

def edit_blog():

    if not m.check_credentials('blog.edit_blog', g.SEC.get('USER_ID',-1) ):
        return m.log_in_page()

    if 'blog_id' in g.GET:
            _key = int(g.GET['blog_id'])
    elif 'blog_id' in g.POST:
           _key = int(g.Post['blog_id'])

    if _key == -1:
        return False

    _sql = "select blog_title, blog_htmltext from blog where blog_id = %(blog_id)s;"

    _rec = m.run_sql_command(_sql, {'blog_id':_key})
    if len(_rec) == 0 :
        return False
    g.CONTEXT.update({'submit_command':'save_blog',
                      'blog_id':_key, 
                      'title': _rec.get('blog_title',''),
                      'content':_rec.get('blog_html','')
                    })
    return True 

def new_blog():
    g.CONTEXT.update({'blog_id' : m.get_db_next_id("blog_blog_id_seq"),
                    'submit_command': 'save_blog'}
                    )
    return True

def save_blog():
    if 'blog_id' in g.GET :
        _key = int(''.join(g.GET.get('blog_id')),'-1')
        _search_tags = ''.join(g.GET.get('search_tags', '')).split(',')
        _text = ''.join(g.GET.get('content', ''))
        _title = ''.join(g.GET.get('title', ''))
    elif 'blog_id' in g.POST:
        _key = int(''.join(g.POST.get('blog_id','-1')))
        _search_tags = ''.join(g.POST.get('search_tags', '')).split(',')
        _text = ''.join(g.POST.get('content', ''))
        _title = ''.join(g.POST.get('title', ''))
    else  :
        return False
    
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
            search_tags = %(search_tags)s ,
            tvs = to_tsvector(%(tvs)s),
            blog_title =%(blog_title)s
        where  blog_id = %(blog_id)s
    );"""

    _topadd = { 'blog_id': _key,
            'blog_user_id':int(g.SEC.get('USER_ID',-1)),
            'blog_htmltext': _text,
            'search_tags': _search_tags,
            'tvs':extext(_text),
            'blog_title': _title

    }
    m.run_sql_command(_sql, _topadd)
    return get_blog_by_id(_key)

"""
 _missing = m.test_for_entries_in(['title', 'comment', 
                                'tags', 'author', 
                                'date_posted',
                                'category',],
                                g.GET    
                            )
        if len(_missing) >0:
            m.error('The following form fields are missing %s' 
                % (', '.join(_missing), 'edit_blog') 
            )
            return False
"""

def commit_blog(p_user =-1 , pblog_id =-1, p_htmltext='', p_tags='', p_title='',  ):
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
    con = g.CONN['PG1'] 
    cur = con.cursor()
    cur.execute(q_str, _topass)
    _rec = cur.fetchall()
    if len(_rec)>0:
        return _rec[0][0]
    return -1

def get_cats():
    q_str= """ select  '?id=' || cat_id::text as url, cat_short as Name, 
                cat_long || ' ' ||  coalesce(bl_count, 0)::text as LinkText
            from category 
                left join ( select count(*) as bl_count, 
                                bl_cat_id from blog_cats 
                                group by bl_cat_id ) bl
                    on bl_cat_id = cat_id 
    """
    con = g.CONN['PG1'] 
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q_str)
    _rec = cur.fetchall()
    _cat = m.build_url_links( _rec, p_app_command='view_category')
    
    g.CONTEXT.update({'category': _cat})

def view_category():
    pass

def get_blog_counts(p_id):
    q_str = """ select bc_views 
                from blog_counter where bc_blog_id = %(id)s  """
    con = g.CONN['PG1'] 
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q_str, {'id': p_id})
    _rec = cur.fetchall()
    g.CONTEXT.update({'web_urls':  m.build_url_links(_rec)}) 
    return True 

def get_blog_view_counts(p_id):
    q_str = """ select blog_title as Name, 
                        blog_title || coalesce(bc_views, 0)::text as LinkText,
                        '?id='||blog_id::text as url
                from blog 
                    left join blog_counter on blog_id = bc_blog_id
                order by blog_counter desc limit 5  """
    con = g.CONN['PG1'] 
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q_str)
    _rec = cur.fetchall()
    g.CONTEXT.update({'web_urls':  m.build_url_links(_rec)}) 
    return True 

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
