# pyUweb
light-weight web frame work for python for embedded hardware like raspberry pie or other min hardware

It uses the python mod_wsgi interface so it will work with several different webservers.

follow the mod_wsgi intructions for desired webserver 
https://modwsgi.readthedocs.io/en/develop/
https://modwsgi.readthedocs.io/en/develop/user-guides/quick-installation-guide.html


The HTML redenering engine usesd is ctemplate-python https://github.com/zsheep5/ctemplate-python

There is alot of work to do 
1:cookies set and read buiding a global Dictionary cookies

2: user session enviroment saved between http request.  intent is used avoid pypickle use straight JSON to python dictionaries. The JSON document is stored back to Postgresql database. 

3: to be only use functional style web frame work

4: avoid the use of ORM 



