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
            _key = int(g.GET['blogkey'])
    elif 'blogkey' in g.POST:
           _key = int(g.Post['blogkey'])
    if get_blog_by_id(_key):
        return False
    get_comments(_key)
    get_blog_view_counts()
    get_cats()
    
    return True

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
    con = g.CONN['PG1'] 
    cur = con.cursor()
    cur.execute(q_str, { 'search_value':_text } )
    _rec = cur.fetchall()
    if len(_rec) > 0:
        _cat = []
        for _r in _rec:
            _cat.append({'blog_url': 
                        build_get_url('view',
                                {'blogkey':_r[0]}
                            ),
                        'blog_title':_r[1],
                        'blog_date': _r[2],
                        'blog_text_250':html2text(_r[3])[0:250],
                        'rank':_r[4]
                    }
                )
        g.CONTEXT.update({'search_results':_rec[0]})
        return True

    return False

def get_blog_by_id(pid = -1):  ##should always return  record set in the form list of list 
    q_str = """select blog_id, blog_user_id,  blog_title, blog_date, 
                blog_htmltext, search_tags 
        from blog  """
    if pid < 0: 
        q_str += """ order by blog_date desc """
    else :
        q_str += """ where blog_id = %(blogid)s""" 
    con = g.CONN['PG1'] 
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q_str, { 'blogid':pid } )
    _rec = cur.fetchall()
    if len(_rec) > 0:
        g.CONTEXT.update({'blog':_rec[0]})
        return True

    return False

def insert(named_list= []): ##returns the records inserted send in the list 
    return None

def delete(ids=[]): ##past a list of the primary IDs to delete.
    return True

def get_blogs_list(search_by, offset=0, limit=25):
    pass

def build_pager():
    pass

def get_more_results(p_id = -1, p_offset=0, p_limit=50):
    pass 

def get_comments(p_id =-1, p_offset=0, p_limit=50):
    q_str = """ select bc_id , bc_blog_id , bc_bc_parent,
	            bc_user_id,	bc_date_id, bc_comment, bc_tvs
                from  blog_comments where
                bc_blog_id  = %(blogid)s 
                limit %(p_limit)s  offset %(p_offset)s 
                """
    con = g.CONN['PG1'] 
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q_str, { 'blogid':p_id, 'p_limit': p_limit, 'p_offset': p_offset } )
    _rec= cur.fetchall()
    if len(_rec) > 0:
        g.CONTEXT.update({'comments':_rec})
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
    _key = -1
    if not m.check_credentials('blog.edit_blog', g.SEC['USER_ID'], ):
        return m.log_in_page()

    if 'blogkey' in g.GET:
            _key = int(g.GET['blogkey'])
    elif 'blogkey' in g.POST:
           _key = int(g.Post['blogkey'])
    
    if _key == -1:
        _key = m.get_db_next_id('blog_blog_id_seq')
        if _key == -1:
            return False
        g.CONTEXT.update({'mode':'new',
                        'blogkey':_key, 
                        }
                        )
    else :
        _missing = m.test_for_entries_in(['title', 'html_text', 
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
        add_blog(
            p_user = ''
        )
        
    return False

def new_blog():
    g.CONTEXT.update({'blog_id' : m.get_db_next_id("blog_blog_id_seq"),
                    'save_blog': 'save_blog'}
                    )
    return True

def save_blog():
    if 'blog_id' in g.GET and 'blog_text' in g.GET and 'blog_title' in g.GET:
            _key = int(g.GET['blogkey'])
            _text = g.GET.get('blog_text')
    elif 'blog_id' in g.POST:
           _key = int(g.Post['blogkey'])
    else:
        m.error('No ID key found get or post dictionaries', 'blog.save_blog')
    



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
    q_str= """ select  cat_id, cat_short, 
                coalesce(bl_count, 0) as cat_count
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
    _cat = []
    for _r in _rec:
        _cat.append({'cat_url': build_get_url('view_cat',
                                { 'cat_id':_r['cat_id']}
                                ),
                        'cat_name':_r['cat_short'],
                        'cat_count': _r['cat_count']
                    }
                )
    g.CONTEXT.update({'category': _cat})

def get_blog_view_counts():
    q_str = """ select blog_id, blog_title, 
                        coalesce(bc_views, 0) as bc_views 
                from blog 
                    left join blog_counter on blog_id = bc_blog_id
                order by 3 desc limit 5  """
    con = g.CONN['PG1'] 
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q_str)
    _rec = cur.fetchall()
    _tops = []
    for _r in _rec:
        _tops.append({'top_url': build_get_url('view',
                                { 'blog_id':_r['blog_id']}
                                ),
                        'blog_title':_r['blog_title'],
                    }
                )
    g.CONTEXT.update({'tops': _tops})  

def up_blog_view_count(p_id=-1):
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

def POST(_post):
    return True 

def GET(_get):
    return True