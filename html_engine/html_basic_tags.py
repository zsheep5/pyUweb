
def table( ):
    return ''

#constructs a html table send in the number columns
# then a list of colors, used 
#precords assumed to be a list of list per python 
def table_row(  precords=[],
                pcolumn_count=-1,
                pheader_names = [],
                border=[],
                pwidth=[],
                pheight=[],
                pcolors=[],
                palternate_background=[],
                pcss =''  ):
    _return = ''
    if pcss != '': ## CSS rules sent in ignore wieght height colors
        pwidth=[],
        pheight=[],
        pcolors=[],
        palternate_background=[]
        _return += """<style>%s</style>""",(pcolors)
    else:
        _return = ''
        if pcolumn_count !=len(pheader_names):
            _return += ' number of columns to create does not match header name count'
        if pcolumn_count !=len(pwidth):
            _return += ' number of columns to create does not match number width declared '
        if pcolumn_count !=len(pcolors):
            _return += ' number of columns to create does not number of colors declared '
        if len(_return) > 0:
            return _return 
    
    for _r in pheader_names: 
    for _r in precords:
        _return += """  
"""
    return ''