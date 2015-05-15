# coding=utf-8
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
"""
Module to tie the quantities, calculator, and form modules together into an online calculator.

The calculator is hosted on ktheis.pythonanywhere.com, but you could have a local server or run it
on other platforms. In the calculator, you define values of named physical quantities,
and then do arithmetic with them. The web server is implemented using web.py.

"""
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
    '/custom', 'preload',
    '/(js|css|png|ico)/(.*)', 'static',
    '/example(.*)', 'example'
)

import sys

sys.path.append("/var/www")

from calculator import calc, gather_symbols
from form import newform, printableLog, helpform


class index:
    """
    Defines the home page of the PQCalc server.

    """
    def GET(self):
        web.header('Content-Type', 'text/html; charset=utf-8', unique=True)
        known = [" -- nothing yet -- "]
        browser = web.ctx.env['HTTP_USER_AGENT'].lower()
        mobile = ("ipad" in browser or "iphone" in browser or "ipod" in browser)
        if "ipod" in browser or "iphone" in browser or "android" in browser:
            mobile = "ipod"
        return newform("", "", "", known, "", mobile, False, "")


    def POST(self):
        """
        Load quantities defined previously by the user, process current commands and output results.
        """

        web.header('Content-Type', 'text/html; charset=utf-8', unique=True)
        browser = web.ctx.env['HTTP_USER_AGENT'].lower()
        mobile = ("ipad" in browser or "iphone" in browser or "nexus" in browser)
        if "ipod" in browser or "iphone" in browser or "android" in browser:
            mobile = "ipod"
        try:
            state = web.input()
            if state['sub'] == "reset":
                return newform("", "", "", "", "", mobile, False, "")
        except:
            return newform("", "", "", "", "", mobile, False, "")

        oldsymbols = state['memory']
        logbook = state['logbook']
        inputlog = state['inputlog']
        if state['sub'] == "export":
            allsymbols, symbollist = gather_symbols(oldsymbols)
            return printableLog(allsymbols, symbollist, logbook, inputlog)
        if state['sub'] == "help":
            return helpform(mobile)
        commands = state['commands']
        inputlog = inputlog + "\n" + commands
        outp, logp, mem, known, mobile, oneline = calc(oldsymbols, commands, mobile)
        return newform(outp, logp, mem, known, logbook, mobile, oneline, inputlog)


class static:
    def GET(self, media, file):
        try:
            f = open('static/' + file, 'r')
            return f.read()
        except:
            return 'bull %s %s' % (media, file)  # you can send an 404 error here if you want


class example:
    """
    Shows the PQCalc form pre-filled with example calculation commands.
    """
    def GET(self, examplenr):
        web.header('Content-Type', 'text/html; charset=utf-8', unique=True)
        browser = web.ctx.env['HTTP_USER_AGENT'].lower()
        known = ["nothing yet"]
        prefill = examplenr
        mobile = ""
        mobile = ("ipad" in browser or "iphone" in browser or "nexus" in browser)
        if "ipod" in browser or "iphone" in browser:
            mobile = "ipod"
        return newform("", "", "", known, "", mobile, False, "", prefill=prefill)

class preload:
    """
    Defines the home page of the PQCalc server with switches loaded.

    """
    def GET(self):
        web.header('Content-Type', 'text/html; charset=utf-8', unique=True)
        browser = web.ctx.env['HTTP_USER_AGENT'].lower()
        mobile = ("ipad" in browser or "iphone" in browser or "nexus" in browser)
        if "ipod" in browser or "iphone" in browser or "android" in browser:
            mobile = "ipod"
        try:
            state = web.input(switch="")
            if state['switch'] == "":
                return newform("", "", "", "", "", mobile, False)
        except:
            return newform("", "", "", "", "", mobile, False)

        oldsymbols = ""
        logbook = ""
        commands = "\n".join(["__%s__ = 1" % switch for switch in state['switch'].split("*")])
        outp, logp, mem, known, mobile, oneline = calc(oldsymbols, commands, mobile)
        return newform(outp, logp, mem, known, logbook, mobile, oneline, "")

# comment out these two lines if you want to use another framework
if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
