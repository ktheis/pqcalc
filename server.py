# This file contains the WSGI configuration required to serve up your
# web application at http://<your-username>.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler of some
# description.


# +++++++++++ WEB.PY +++++++++++
# Here is a simple web.py app. It is currently serving the default welcome
# page.  You can adapt this if you want
# If you're using a different web framework, you'll need to comment all this
# out

import web
urls = (
  '/', 'index',
  '/(js|css|png)/(.*)', 'static',
  '/example(.*)', 'example'
)

import sys
sys.path.append("/var/www")

import quantities
from calculator import calc
from quantities import Q, Units, unitquant, functions, number2quantity, math_name
from forms import newform, printableLog
 
class index:
    def GET(self):
        web.header('Content-Type','text/html; charset=utf-8', unique=True)
        known = [" -- nothing yet -- "]
        browser = web.ctx.env['HTTP_USER_AGENT'].lower()
        mobile = ""
        mobile = ("ipad" in browser or "iphone" in browser or "ipod" in browser)
        if "ipod" in browser or "iphone" in browser or "android" in browser:
            mobile = "ipod"
        return newform("", "", "", known, "", mobile)

    def POST(self):
        web.header('Content-Type','text/html; charset=utf-8', unique=True)
        browser = web.ctx.env['HTTP_USER_AGENT'].lower()
        mobile = ""
        mobile = ("ipad" in browser or "iphone" in browser or "nexus" in browser)
        if "iphone" in browser:
            mobile = "ipud"
        try:
            state = web.input()
            if state['sub'] == "start over":
                return newform ("", "", "", "", "", mobile)
        except:
            return newform ("", "", "", "", "", mobile)

        oldsymbols = state['memory']
        logbook = state['logbook']
        if state['sub'] == "printable view":
            allsymbols = {}
            symbollist = []
            if oldsymbols:
                old = oldsymbols.split('\r\n')
                for a in old:
                    sym = a.split("'")[1]
                    allsymbols[sym] = eval(a)
                    symbollist.append(sym)
            return printableLog (allsymbols, symbollist, logbook)
        commands = state['commands']
        outp, logp, mem, known, mobile = calc(oldsymbols, commands, mobile)
        #outp.append("<PRE>%s</PRE>"  % mobile)
        return newform (outp, logp, mem, known, logbook, mobile)

class static:
    def GET(self, media, file):
        try:
            f = open('/var/www/static/'+file, 'r')
            return f.read()
        except:
            return 'bull %s %s' % (media, file) # you can send an 404 error here if you want

class example:
    def GET(self, examplenr):
        web.header('Content-Type','text/html; charset=utf-8', unique=True)
        browser = web.ctx.env['HTTP_USER_AGENT'].lower()
        known = ["nothing yet"]
        prefill = examplenr
        mobile = ""
        mobile = ("ipad" in browser or "iphone" in browser or "nexus" in browser)
        if "ipod" in browser or "iphone" in browser:
            mobile = "ipod"
        return newform("", "", "", known, "", mobile, prefill = prefill)


# comment out these two lines if you want to use another framework
if __name__ == "__main__": 
    app = web.application(urls, globals())
    app.run()
