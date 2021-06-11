"""Standalone local Viewer
An app to view multiple EdgarRenderer reports rendered using `arellepy.CntlrPy.renderEdgarReports` together, 
the app starts in a seprate process, can be started from commandline:

    python LocalViewerStandalone.py --appDir /path/to/Arelle/installation 
                                  --host 0.0.0.0 
                                  --lookinFolders '/path/to/folder1|path/to/folder1'
                                  --edgarDir '/path/to/EdgarRenderer' # if not using EdgarRenderer in default Arelle/arelle/plugin folder

or from python after setting up the environment:

>>> sys.path.append('/path/to/arellepy')
>>> from arellepy.HelperFuncs import selectRunEnv
>>> selectRunEnv(env=runEnv, workingDir=wkngsDir, appDir=insldAppDir, srcDir=srcDir)
>>> from arellepy.LocalViewerStandalone import LocalViewerStandalone
>>> v = LocalViewerStandalone(appDir='/path/to/Arelle/installation', host='0.0.0.0', lookInFolders='path/to/folder1|path/to/folder1')
>>> p, h = v.startViewer(asDaemon=True)
>>> p.terminate() # To terminate the process

or from Arelle gui, import arellepy plugin and an icon will appear in the tool bar to launch this app.
"""

import sys, os, argparse, socket, logging, threading, gettext, datetime, json, urllib.request, urllib.error
from arelle.CntlrWinTooltip import ToolTip
pathToLocals = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locals')

from dateutil.relativedelta import relativedelta
import lxml.etree as et

import tkinter as tkr
from tkinter import filedialog
from tkinter import messagebox
try:
    import tkinter.ttk as ttk
except ImportError:
    import ttk


try:
    from .HelperFuncs import makeLocator, chkToList, selectRunEnv
except:
    from HelperFuncs import makeLocator, chkToList, selectRunEnv


hasArelle = False
try:
    from arelle.webserver.bottle import Bottle, static_file, request, abort, redirect
    hasArelle = True
except:
    Bottle, static_file, request, abort, redirect = (None,)*5

def main():
    gettext.install("arelle") # needed for options messages
    opts = optionsHandler()
    opts.parseOpts()
    viewer = LocalViewerStandalone( appDir=opts.args.appDir, edgarDir=opts.args.edgarDir,
                                    lookInFolders=opts.args.lookInFolders, host=opts.args.host,
                                    quiet=opts.args.quiet, debug=opts.args.debug, reloader=opts.args.reloader,
                                    port=opts.args.port)  
    x = viewer.startViewer()
    # print(x[1])

class optionsHandler:
    def __init__(self):
        self.args = None
        parser = argparse.ArgumentParser(description='Runs an Instance of Local Viewer')
        parser.add_argument('--workingDir', metavar='workingDir', type=str, dest='workingDir', default='',
                            help=_('Location of working dir - for debuging (path)'))
        parser.add_argument('--appDir', metavar='appDir', type=str, dest='appDir', default='',
                            help=_('Location of arelle app (path)'))
        parser.add_argument('--srcDir', metavar='srcDir', type=str, dest= 'srcDir', default= '',
                            help=_('Location of arelle source dir (source code) - for debuging (path)'))
        parser.add_argument('--edgarDir', metavar='edgarDir', type=str, dest= 'edgarDir', default= '',
                            help=_('Location of Edgar plugin, defaults to "appDir/plugin/EdgarRenderer"'))
        parser.add_argument('--env', metavar='Environment', type=str, dest= 'env', default= 'app', choices=['app', 'src'],
                            help=_('Select run environment - for debuging (path)'))
        # parser.add_argument('--localsDir', metavar='LocalsDir', type=str, dest='localsDir',
        #                     help=_('Location of viewer local files'), default=pathToLocals)
        parser.add_argument('--lookinFolders', '-l', metavar='path', type=str, dest='lookInFolders', nargs='+', default=None,
                            help=_('Locations to look for reports folders generated by EdgarRenderer'))
        parser.add_argument('--host', '-hst', metavar='host', type=str, dest='host', default='localhost',
                            help=_('Host for bottle app (default: localhost)'))
        parser.add_argument('--server', '-s', metavar='servertype', type=str, dest='server', default='cheroot',
                            help=_('Server for bottle app (default: cheroot)'))
        parser.add_argument('--port', '-p', metavar='port', type=str, dest='port', default=None,
                            help=_('Port number for bottle app'))
        parser.add_argument('--quiet', '-q', metavar='bool', type=bool, dest='quiet', default=False,
                            help='bottle server quite option - bool (default: False)')
        parser.add_argument('--debug', '-d', metavar='bool', type=bool, dest='debug', default=False,
                            help=_('bottle server debug option - bool (default: False)'))
        parser.add_argument('--reloader', '-r', metavar='bool', type=bool, dest='reloader', default=False,
                            help=_('bottle server reloader option - bool (default: False)'))

        self.parser = parser

    def parseOpts(self):
        global hasArelle
        self.args = self.parser.parse_args()
        if not hasArelle:
            setEnv(workingDir=self.args.workingDir, env=self.args.env, appDir=self.args.appDir, srcDir=self.args.srcDir)

def setEnv(workingDir=None, env=None, appDir=None, srcDir=None):
    global Bottle, static_file, request, abort, redirect
    # Make sure WorkingsDir is in path
    if workingDir:
        if workingDir not in sys.path: # for debugging current working dir
            sys.path.append(workingDir)
    # setup appropriate cwd and sys.path entries, using 'selectRunEnv' function, when selecting
    # "app" it sets up the cwd and 'sys.path' to memic app envrionment, when selecting 'src'
    # it sets up the cwd and 'sys.path' to point to the sorce code (downloaded from github).
    selectRunEnv(env=env, workingDir=workingDir, appDir=appDir, srcDir=srcDir)
    from arelle.webserver.bottle import Bottle, static_file, request, abort, redirect

class LocalViewerStandalone:
    def __init__(self, appDir, edgarDir=None, lookInFolders=None, host='localhost', 
                    quiet=True, debug=False, reloader=False, port=None):
        # After setting up environment
        if not edgarDir:
            edgarDir = [os.path.join(appDir, 'plugin/EdgarRenderer')]
        self.appDir = appDir 
        lookInFolders_list = [] 
        if lookInFolders:
            if isinstance(lookInFolders, str):
                lookInFolders_list.extend(lookInFolders.split('|'))
            elif isinstance(lookInFolders, list):
                for x in lookInFolders:
                    lookInFolders_list.extend(x.split('|'))
        self.lookInFolders = chkToList(lookInFolders_list, str, os.path.exists) if lookInFolders_list else []
        self.reportsFolders = chkToList(edgarDir,str) #[os.path.join(appDir, 'plugin/EdgarRenderer')]
        self.localsDir = pathToLocals
        self.viewerHome = 'viewerHome.html'
        self.locator = makeLocator(self.lookInFolders)['locators'] if self.lookInFolders else dict()
        self.server = 'cheroot'
        self.host = host #'localhost'
        self.quiet = quiet #True
        self.debug = debug #False
        self.reloader = reloader #False
        self.port = port

        # App and routes
        self.localserver = Bottle()
        self.localserver.route('/getLoc', 'GET', self.refreshLocator)
        self.localserver.route('/getLookinFolders', 'GET', self.getLookinFolders)
        self.localserver.route('/selectLookinFolders', 'GET', self.selectLookinFolders)
        self.localserver.route('/changeLookinFolders', 'POST', self.changeLookinFolders)
        self.localserver.route('/EdgarLink', 'GET', self.edgarLink)
        self.localserver.route('/home', 'GET', self.home)
        self.localserver.route('/', 'GET', self.home)
        self.localserver.route('/<file:path>', 'GET', self.getlocalfile)


    def getEdgarFilingLink(self, filingData: list): # dataAttrs list
        """Tries to get Edgar index page for a filing based on cik, form type and report date""" 
        _l = self.locator.get(filingData[-1], '')
        l = _l.get('indexLink')[1]
        if not l:
            vals = filingData
            cik = vals[0]
            formType = vals[1].upper()
            reportDate = datetime.datetime.strptime(vals[2], '%Y-%m-%d').date()
            filingDate = datetime.datetime.strptime(vals[3], '%Y-%m-%d').date()
            datea = filingDate if filingDate else reportDate
            dateb = filingDate if filingDate else reportDate + relativedelta(years=1)
            
            if formType == '10-Q' and not filingDate:
                dateb = reportDate + datetime.timedelta(days=46)
            elif formType == '10-K' and not filingDate:
                dateb = reportDate + datetime.timedelta(days=91)
            feed = (
                'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={}'
                '&type={}&datea={}&dateb={}&owner=exclude&start=0&count={}&output=atom'
            ).format(cik, formType, datea, dateb, 1)
            feedpage = urllib.request.urlopen(feed)
            feedTree = et.parse(feedpage).getroot()
            # feedTree.xpath('.//*[local-name()="filing-date"]')[0].text
            try:
                l = feedTree.xpath('.//*[local-name()="entry"]/*[local-name()="link"]')[0].get('href')
            except:
                l = ''
        return l

    def getlocalfile(self, file=None):
        '''Based on EdgarRenderer/LocalViewer.py'''
        try:
            if file == 'favicon.ico':
                return static_file("Edgar.png", root=pathToLocals, mimetype='image/vnd.microsoft.icon')
            _report, _sep, _file = file.partition("/")
            if _report == "filing" and _file.endswith('ix.html'):
                _key, _s, _tail = _file.partition('/')
                targetDir = self.locator[_key]['reportFolder']
                fileName = _key.replace('_', '.')
                primDoc = os.path.basename(self.locator[_key]['primeDoc'][1])
                if self.locator[_key]['card-inlineXbrl'][1] == 'Yes':
                   redirect("/home/ix.html?doc=/filing/{}/{}&xbrl=true".format(_key, primDoc))
                else:
                    return static_file(primDoc, targetDir)
            if _report == "filing": # filing folder
                _key, _s, _f = _file.partition('/')
                targetDir = self.locator[_key]['reportFolder']
                return static_file(_f, targetDir)
            if _report == 'locals':
                return static_file(_file, self.localsDir)
            if (_file.startswith("ix.html") # although in ixviewer, it refers relatively to ixviewer/
                or _file.startswith("css/")
                or (_file.startswith("images/") and os.path.exists(os.path.join(self.reportsFolders[0], 'ixviewer', _file)))
                or _file.startswith("js/")):
                return static_file(_file, root=os.path.join(self.reportsFolders[0], 'ixviewer'))
            if _report == "include": # really in include subtree
                return static_file(_file, root=os.path.join(self.reportsFolders[0], 'include'))
            if _file.startswith("include/"): # really in ixviewer subtree
                return static_file(_file[8:], root=os.path.join(self.reportsFolders[0], 'include'))
            if _file.startswith("ixviewer/"): # really in ixviewer subtree
                return static_file(_file[9:], root=os.path.join(self.reportsFolders[0], 'ixviewer'))
        except Exception as ex:
            raise ex

    def home(self):
        return static_file(self.viewerHome, self.localsDir)

    # Click refresh button in viewer
    def refreshLocator(self):
        self.locator = makeLocator(self.lookInFolders)['locators'] if self.lookInFolders else dict()
        return self.locator

    # tkinter select dir to select dir to look for filings
    def selectLookinFolders(self):
        root = tkr.Tk()
        root.title("Select Folder")
        root.geometry('0x0')
        root.attributes('-alpha', 0)
        root.attributes('-topmost', True)
        root.withdraw()
        _folder = filedialog.askdirectory(parent=root, initialdir=self.appDir)
        root.destroy()
        return _folder

    def getLookinFolders(self):
        return json.dumps(self.lookInFolders)

    def changeLookinFolders(self):
        received = request.json
        changed = not sorted(self.lookInFolders) == sorted(received)
        self.lookInFolders = received
        return json.dumps(changed)

    def edgarLink(self):
        try:
            filingInfos = [request.query.cik, request.query.formType, 
                            request.query.reportDate, request.query.filingDate, 
                            request.query.route]
            redirect(self.getEdgarFilingLink(filingInfos))
        except urllib.error.URLError:
            abort(500, "Could not connect to Edgar")
    
    def init(self):
        self.localserver.run(server=self.server, 
                            port= self.port, 
                            host=self.host, 
                            quiet=self.quiet, 
                            debug=self.debug, 
                            reloader=self.reloader)
                            
    def startViewer(self, asDaemon=True, threaded=True):
            # workingDir: str=None, appDir: str=None, srcDir: str = None, env: str = 'app', localsDir: str = None,
            # lookinFolders: str = None, host: str = 'localhost', quiet: bool = False,
            # port: int = None, server: str = 'cheroot', debug: bool = False,
            # reloader: bool = False):
        """Starts viewer in another Thread"""
        if not self.port:
            # find available port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", 0))
            s.listen(1)
            self.port = str(s.getsockname()[1])
            s.close()

        xhost = self.host
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            xhost = s.getsockname()[0]
        finally:
            s.close()
        
        landingPage = "http://{}:{}/home".format(xhost, self.port)
        p = None

        if threaded:
            p = threading.Thread(target=self.init, daemon=asDaemon)
            p.start()
        else:
            self.init()
        
        return (p, landingPage)

def initViewer(cntlr, lookinFolders=None, edgarDir=None, threaded=True, asDaemon=True):
    _lookinFolders = lookinFolders
    if cntlr.hasGui:
        _lookinFolders = filedialog.askdirectory(title=_("Select a directory containing Edgar Filings"), parent=cntlr.parent)
    appDir = os.path.dirname(cntlr.configDir)
    if not edgarDir:
        edgarDir = os.path.join(appDir, 'plugin/EdgarRenderer')

    if not os.path.isdir(edgarDir):
        if cntlr.hasGui:
            getEd = messagebox.askyesno(title='Edgar Viewer Info', 
                                        message='This feature requires EdgarRenderer Plugin\nChoose the location of EdgarRenderer plugin?',
                                        parent=cntlr.parent)
            if getEd:
                edgarDir = filedialog.askdirectory(title=_("Select EdgarRenderer Directory"), parent=cntlr.parent)
            else:
                messagebox.showinfo(title='RSS DB info', message='Aborting Viewer...', parent=cntlr.parent)
                return
            if not os.path.isdir(edgarDir):
                messagebox.showinfo(title='RSS DB info', message='Couldnot find EdgarRenderer plugin, please enter valid location for the plugin\nAborting...', parent=cntlr.parent)
                return
        else:
            cntlr.addToLog(_("This feature requires EdgarRenderer plugin, please enter a valid value for edgarDir. Aborting Viewer..."), 
                                messageCode="EdgarViewer.Info",  file="",  level=logging.INFO)
            return

    v = LocalViewerStandalone(appDir=appDir, host='0.0.0.0', lookInFolders=_lookinFolders, edgarDir=edgarDir)
    cntlr.edgarViewerProcess = v.startViewer(asDaemon=asDaemon, threaded=threaded)
    _msg = (_('Local Edgar viewer started at {}').format(cntlr.edgarViewerProcess[1]))
    cntlr.addToLog(_msg, messageCode="EdgarViewer.Info",  file="",  level=logging.INFO)
    if cntlr.hasGui:
        messagebox.showinfo(_('Local Edgar viewer'), 'Local Viewer app started at: {}'.format(cntlr.edgarViewerProcess[1]), parent=cntlr.parent)

def startEdgarViewer(cntlr, makeNew=False, edgarDir=None, threaded=True):
    proc = getattr(cntlr, 'edgarViewerProcess', None)
    if proc and proc[0].is_alive():
        if cntlr.hasGui:
            makeNew = messagebox.askyesno(title=_('Local Edgar viewer'), 
                                    message=(_('There is an existing dashboard runing at\n{}\n'
                                                'Do you wish to terminate it and run a new one?')).format(proc[1]), parent=cntlr.parent)
        if makeNew:
            try:
                cntlr.edgarViewerProcess[0].terminate()
                _msg = (_('Local Edgar viewer at {} is terminated').format(cntlr.edgarViewerProcess[1]))
                cntlr.addToLog(_msg, messageCode="EdgarViewer.Info",  file="",  level=logging.INFO )
                initViewer(cntlr=cntlr, edgarDir=edgarDir, threaded=threaded)
            except Exception as e:
                cntlr.addToLog(str(e), messageCode="EdgarViewer.Error",  file="",  level=logging.ERROR)
                if cntlr.hasGui:
                    messagebox.showerror(_("Local Edgar viewer error(s)"), str(e), parent=cntlr.parent)
        else:
            return
    else:
        try:
            initViewer(cntlr=cntlr, edgarDir=edgarDir)
        except Exception as e:
            cntlr.addToLog(str(e), messageCode="EdgarViewer.Error",  file="",  level=logging.ERROR)
            if cntlr.hasGui:
                messagebox.showerror(_("Local Edgar viewer error(s)"), str(e), parent=cntlr.parent)

def toolBarExtender(cntlr, toolbar):
    if cntlr.isMac:
        toolbarButtonPadding = 1
    else:
        toolbarButtonPadding = 4

    tbControl = ttk.Separator(toolbar, orient=tkr.VERTICAL)
    column, row = toolbar.grid_size()
    tbControl.grid(row=0, column=column, padx=6)
    image = os.path.join(pathToLocals, 'Edgar.png')
    image = tkr.PhotoImage(file=image)
    cntlr.toolbar_images.append(image)
    tbControl = ttk.Button(toolbar, image=image, command= lambda: startEdgarViewer(cntlr,), style="Toolbutton", padding=toolbarButtonPadding)
    ToolTip(tbControl, _('Launch Edgar reports viewer'))
    column, row = toolbar.grid_size()
    tbControl.grid(row=0, column=column)


if __name__ == "__main__":
    main()
