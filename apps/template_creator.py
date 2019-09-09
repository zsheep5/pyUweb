
"""
Contains functions to access certain aspects of the database
to create forms and basic layouts simplify creating templates.
"""
import globals as g 
import pyUweb as m 

def build_html_template( p_table_name, p_template_name ):
    pass

def create_html_entry(p_id, p_description, p_table_name, p_func_name, p_template_stack, p_css):
    pass

def create_app_stack_skelton( p_table_name, p_app_name, p_file_name  ):
""" this assums the table has been defined in the databae and uses that to create function skelton
app_stack, app_template, entries, and template_skelton.
""" 
    _f = open(p_file_name+'.py', wr)


def build_appstack_skelton(p_app_name, p_file_name ):
    return """
        '%(app_name)s':{
             'template_stack':'%(p_app_name)s',
            'filename':'%(p_file_name)s', 
            'path':'.',
            'command':'init' , 
            'security':False,
            'content_type': 'text/html',
            'server_cache_on':True,
            'server_cache_age':30,
            'cacheability':'private',
            'cache_age':30, 
            }
    """ % {'app_name':p_app_name, p_file_name}

def build_template_stack_skelton(p_app_name, p_include_templates=[] ):
  
  p_list = "'" + "','".join(p_include_templates) + "'"
  return"""  '%(p_app_name)s':['%(p_app_name)s', 
            ],
        """


_skelton = """
import session_controller  as sc
import pyUwf as m
import psycopg2, psycopg2.extras 
from html2text import html2text as extext
from urllib.parse import quote_plus as qp 

def init(POST, GET, ENVIRO, CLIENT_STATE,  COOKIES, CONTEXT, TEMPLATE, TEMPLATE_ENGINE):
    pass
    
    #any function you create should be modeled after the init function above as run_py passes in these variables into the function call

    
    

def render_template(CONTEXT, TEMPLATE, TEMPLATE_ENGINE):
    pass

"""


