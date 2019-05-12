# pyUweb
light-weight web frame work for python for embedded hardware like raspberry pie or other min hardware

It uses the python mod_wsgi interface so it will work with several different webservers.

follow the mod_wsgi intructions for desired webserver 
https://modwsgi.readthedocs.io/en/develop/
https://modwsgi.readthedocs.io/en/develop/user-guides/quick-installation-guide.html


The HTML redenering engine used is ctemplate-python https://github.com/zsheep5/ctemplate-python

add support python wsgiserver  https://pypi.org/project/WSGIserver/
this makes debugging easier 

There is alot of work to do 

1:cookies set and reading are working

2: user session enviroment saved between http request.  intent is to avoid pypickle use straight JSON to python dictionaries. The JSON document is stored in the Postgresql database. 

3: avoid the use of OOP style make a more stream line functional style web frame work




