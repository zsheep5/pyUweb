"""Template stack layout 
 { App_Nane / URL path relative website root
   [ list of html files that make up template.  ]
 }
 files must be in the template_path you can do subdirs but no relative imports
 The idea here is you can include many templates to create big template prior
 to being sent to the render engine.  Ctemplate also have include function
 but the results are thrown away after every call.  building the templates this
 allows for caching the result template.  
 If templates do not use <$TEMPLATE$filename.html$TEMPLATE$>
 flag the proceeding templates are appended at the end in order they show in the list. 
 """ 
def get_ts():
    return {
    '/':['main.html', 
            'blog.html', 
            'blog_comments.html', 
            'search.html'],
    'view':['view_page.html',
            'base.html',
            'top_nav_bar.html',
            'side_bar.html',
            'comments.html',
            'js.html'
        ],
    'list_cats':['list_cats.html',
            'base.html',
            'top_nav_bar.html',
            'js.html'
        ],
    'list':['list_page.html',
            'base.html',
            'top_nav_bar.html',
        ],
    'blog_editor':['edit_blog.html',
            'base.html',
            'top_nav_bar.html',
            'js.html',
        ],
    'log_in':['log_in.html',
            'base.html',
            'top_nav_bar.html',
            'js.html'
        ],
    'error':['error.html'],
    'file':['base.html',
            'top_nav_bar.html',
            'side_bar.html',
            'file.html'],
    'list_cal':['base.html',
                'calibration.html',
                'top_nav_bar_mag.html',
            ],
     'list_cal':['base.html',
                'edit_cal.html',
                'top_nav_bar_mag.html',
            ]
}