""" :mod: `CntlrPy`

Classes and functions used with the CntlrPy subclass of `arelle.CntlrCmdLine.CntlrCmdLine`, this module
defines class `CntlrPy` that can be used interactively in python, this is a convenience for using the same
command line options in an interactive environment such as jupyter notebook or python interactive interpeter.
"""

import os, sys, datetime, json, gettext, logging, time, multiprocessing, shlex, traceback, shutil
from lxml import etree
from collections import OrderedDict, defaultdict
from urllib import request
import arelle
from arelle import (Cntlr, CntlrCmdLine, ModelManager, PluginManager, PackageManager, ModelXbrl,
                    ModelFormulaObject, XmlUtil)
from arelle.FileSource import openFileSource 



try:
    from .HelperFuncs import chkToList, xmlFileFromString, getExtractedXbrlInstance
    from .OptionsHandler import OptionsHandler, RESERVED_KWARGS
except:
    from HelperFuncs import chkToList, xmlFileFromString, getExtractedXbrlInstance
    from OptionsHandler import OptionsHandler, RESERVED_KWARGS

# print('FROZEN STAT:', getattr(sys, 'frozen', 'not frozen!'))

def arelleCmdLineRun(args, configDir=None):
    '''For launching gui from python script...for whatever reason'''
    # prevents duplicating log print on re-runs
    _logger = logging.getLogger('arelle')
    for x in _logger.handlers:
        if type(x).__name__ == 'LogToPrintHandler': # should remove all handlers on run, but this for now
            _logger.removeHandler(x)
    from arelle import CntlrCmdLine
    if os.environ.get("XDG_ARELLE_RESOURCES_DIR"):
        resourcesFunc = CntlrCmdLine.Cntlr.resourcesDir
        CntlrCmdLine.Cntlr.resourcesDir = lambda: os.environ["XDG_ARELLE_RESOURCES_DIR"]
    else:
        raise Exception("useResDir must be set to the location of root dir"
                        "containing resources")
    if configDir:
        if not os.path.isdir(configDir):
            os.mkdir(configDir)
        os.environ['XDG_CONFIG_HOME'] = configDir
    addArgs = '{}--keepOpen'.format('--xdgConfigHome={} '.format(configDir if configDir else ''))
    allArgs =  addArgs + ' ' + args
    args = shlex.split(allArgs)
    gettext.install("arelle")
    c = CntlrCmdLine.parseAndRun(args)
    return c
    


def arelleGuiLaunch(configDir=None):
    '''For launching gui from python script...for whatever reason'''
    from arelle import CntlrWinMain
    if os.environ.get("XDG_ARELLE_RESOURCES_DIR"):
        resourcesFunc = CntlrWinMain.Cntlr.resourcesDir
        CntlrWinMain.Cntlr.resourcesDir = lambda: os.environ["XDG_ARELLE_RESOURCES_DIR"]
    else:
        raise Exception("useResDir must be set to the location of root dir"
                        "containing resources")
    if configDir:
        if not os.path.isdir(configDir):
            os.mkdir(configDir)
        sys.argv.append('--xdgConfigHome={}'.format(configDir))
    
    CntlrWinMain.main()
    
    return

def xResourcesDir():
    """resourcesDir overrides the function in Cntlr module that determines
    the location of resource dirs (config, images, plugins, ...).

    A decision must be made on which directory to use to discover resources
    used by arelle by setting os.environ["XDG_ARELLE_RESOURCES_DIR"], this is done
    through **useResDir** paramater in the CntlrR class.

    This directory should containing the config, images, plugins, locale dirs, in case
    of using arelle source, this should be path ending with "arelle"
    (e.g. '~/Arelle-master/arelle').
    In case of using the app, this should be the insalled app folder
    (e.g. 'c:/Program Files/Arelle').

    Note that in case of the installed app, the arelle library including in "lib"
    while having all the sub folders, it does not conatin the all the necessary files,
    the files are included in the folders on the root of the app dir.

    Returns:
        str -- dirname to be used to set path for the resources dirs
    """
    _resourcesDir = os.environ["XDG_ARELLE_RESOURCES_DIR"]
    return _resourcesDir

class CntlrPy(CntlrCmdLine.CntlrCmdLine):
    """Class doc
    Extends CntlrCmdLine so it can be used interactively in python, uses same arguments used 
    in commandline operations, arguments can be supplied as a dict, or keywords arguments, with
    the result presisted in the interactive environment for more operations.

    args:
        instConfigDir -- absolute path to configration dir to use for this run (cntlr.userAppDir)
        useResDir -- absolute path to arelle library in Arelle installation (~/Arelle/arelle)
        preloadPlugins --  '|' separated string for the names of plugins (example: 'transforms/SEC|validate/EFM') 
                            to preload in order to have there options available when running (see below)
    
    Rest of the arguments are exactly like arelle Cntlr.
    Command line flags (True/False arguments) can be flaged by supplying an empty text for example (validate="") to
    set the validate flag to True.

    usage:
    first the CntlrPy is initialized:
        cntlr = CntlrPy(configDir, useResDir, preloadPlugins='transforms/SEC|validate/EFM')
    then argument are supplied to do whatever operation is required:
        cntlr.runKwargs(file="http://example.com/entryPoint.xml", validate="")
    or

        cntlr.runOpts(
                {
                    "--file" : "http://example.com/entryPoint.xml",
                    "--validate": "" # empty value to flag --validate option as true
                }
            )
    """

    def __init__(self, instConfigDir, useResDir=None, hasGui=False, 
                 logFileName=None, logFileMode=None, logFileEncoding=None, logFormat=None, logLevel=None,
                 logHandler=None, logToBuffer=False, logTextMaxLength=None, logRefObjectProperties=True,
                 loadPlugins=False, loadPackages=False, preloadPlugins=None):
        # Make sure ConfigDir is created
        self.parsedOpts = None
        try:    
            os.makedirs(instConfigDir)
            self.showStatus("Creating Configration Dir at '{}'".format(instConfigDir))
        except FileExistsError:
            self.showStatus("Using Existing ConfigDir at '{}'".format(instConfigDir))

        # Pass instConfigDir to environment variable to be use by Cntlr in
        # locating configration Dir
        os.environ["XDG_CONFIG_HOME"] = instConfigDir

        # Make sure resources dir is selected and assigned to env variable
        # to be used by resourcesDir() in setting resources
        resourcesFunc = None
        if not getattr(sys, 'frozen', False): # do nothing if called from the app
            if useResDir:
                os.environ["XDG_ARELLE_RESOURCES_DIR"] = useResDir
            elif not os.path.isdir(os.environ["XDG_ARELLE_RESOURCES_DIR"]):
                raise Exception("useResDir must be set to the location of root dir"
                                "containing resources")

            resourcesFunc = Cntlr.resourcesDir
            Cntlr.resourcesDir = lambda: os.environ["XDG_ARELLE_RESOURCES_DIR"]

        super().__init__(logFileName=logFileName)
        
        # dir for temporary files generated
        self.userAppTempDir = os.path.join(self.userAppDir, 'temps')
        if not os.path.exists(self.userAppTempDir):
            os.mkdir(self.userAppTempDir)

        if resourcesFunc:
            Cntlr.resourcesDir = resourcesFunc

        # TODO: remove the below until OptionsHandler initialization, overridden by run command
        # start plug in server (requires web cache initialized, but not logger)
        PluginManager.init(self, loadPluginConfig=loadPlugins)

        # requires plugins initialized
        self.modelManager = ModelManager.initialize(self)

        # Add formula options required for validation
        self.modelManager.formulaOptions = ModelFormulaObject.FormulaOptions()

        # start taxonomy package server (requres web cache initialized, but not logger)
        PackageManager.init(self, loadPackagesConfig=loadPackages)

        self.startLogging(logFileName=logFileName, logFileMode=logFileMode,
                          logFileEncoding=logFileEncoding, logFormat=logFormat,
                          logLevel=logLevel, logHandler=logHandler, logToBuffer=logToBuffer, 
                          logTextMaxLength=logTextMaxLength, logRefObjectProperties=logRefObjectProperties 
                          )
        # Cntlr.Init after logging started
        # for pluginMethod in PluginManager.pluginClassMethods("Cntlr.Init"):
        #     pluginMethod(self)

        self.modelManager.loadCustomTransforms()

        # initialize options handler
        self.OptionsHandler = OptionsHandler(self, preloadPlugins=preloadPlugins) 

    # Show stats to keep me entertained while it does its thing
    def showStatus(self, message, clearAfter=None, end='\n'):
        """Doc"""
        print(message, end=end)

    def runOpts(self, optsDict):
        """Runs arguments supplied as key, value dict.

        example:
            cntlr = CntlrPy()
            cntlr.runOpts(
                {
                    "--file" : "http://example.com/entryPoint.xml",
                    "--validate": "" # empty value to flag --validate option
                }
            )
        see CntlrPy.OptionsHandler.dictOptsBySrc() for available options.
        """
        opts = self.OptionsHandler.parseOpts(argsDict=optsDict)
        gettext.install('arelle')
        self.run(opts)

    def convertKwargsToDict(self, **kwargs):
        global RESERVED_KWARGS
        # Deal with reserved python key words (import for importFiles)
        reserved = {v:k for k,v in RESERVED_KWARGS.items()}

        # deal with store_true/false
        _kwargs = dict()
        for k,v in kwargs.items():
            _k = k
            _v = v
            _k = reserved.get(k, None) if reserved.get(k, None) else k
            optAction = self.OptionsHandler.kwargsDict[k]['opt'].action
            if optAction == 'store_true':
                if v:
                    _v = ''
                else:
                    continue
            elif optAction == 'store_false':
                if not v:
                    _v = ''
                else:
                    continue
            elif v is None:
                continue
            else:
                _v = str(v)
            _kwargs[_k] = _v

        # the idea is to work interactively with the model, so keep it open unless closed manually
        # using cntlr.modelManager.close(modelXbrl)
        _kwargs['keepOpen'] = ''

        args =[]
        if _kwargs:
            for k, v in _kwargs.items():
                _kw = "--" + k.replace('_', '-')
                args.append(_kw)
                if v:
                    args.append(v) 

        
        return args


    def runKwargs(self, **kwargs):
        global RESERVED_KWARGS
        """Runs arguments supplied as keyword arguments.

        example:
            cntlr = CntlrPy()
            cntlr.runKwargs(file="http://example.com/entryPoint.xml", validate=True)
        for options that require just 
        see CntlrPy.OptionsHandler.dictOptsBySrc() for available options.
        for `import` keyword (files to import to the DTS) use `imports`
        """
        # Deal with reserved python key words (import for importFiles)
        reserved = {v:k for k,v in RESERVED_KWARGS.items()}

        # deal with store_true/false
        _kwargs = dict()
        for k,v in kwargs.items():
            _k = k
            _v = v
            _k = reserved.get(k, None) if reserved.get(k, None) else k
            optAction = self.OptionsHandler.kwargsDict[k]['opt'].action
            if optAction == 'store_true':
                if v:
                    _v = ''
                else:
                    continue
            elif optAction == 'store_false':
                if not v:
                    _v = ''
                else:
                    continue
            elif v is None:
                continue
            else:
                _v = str(v)
            _kwargs[_k] = _v

        # _kwargs = {reserved.get(k, None) if reserved.get(k, None) else k:v for k,v in kwargs.items()}
        # the idea is to work interactively with the model, so keep it open unless closed manually
        # using cntler.modelManager.close(modelXbrl)
        _kwargs['keepOpen'] = ''
        try:
            opts = self.OptionsHandler.parseOpts(isDict=False, **_kwargs)
        except Exception as e:
            raise e
        gettext.install('arelle')
        self.run(opts)


    def close(self, saveConfig=False, savePlugins=False, savePackages=False, closeLogger=False):
        """Changes cntlr.close() to have more control on what to be save on exit
        
        Closes the controller and its logger, optionally saving the user preferences configuration
           
           :param saveConfig: save the user preferences configuration
           :type saveConfig: bool

           :param savePlugins: save plugin configuration
           :type savePlugins: bool

           :param savePackages: save packages
           :type savePackages: bool
        """
        if savePlugins:
            PluginManager.save(self)
        if savePackages:
            PackageManager.save(self)
        if saveConfig:
            self.saveConfig()
        if closeLogger:
            if self.logger is not None:
                try:
                    self.logHandler.close()
                except Exception: # fails on some earlier pythons (3.1)
                    pass
   


    # Helper methods to identify loaded ModelXbrl -- probably useless
    def get_modelXbrlInfo(self, mdlXbrl: arelle.ModelXbrl.ModelXbrl = None,
                          displayInfo=True, returnObj=False):
        """Gets basic dei information of loaded OR specified modelXbrl"""
        def makeValDict(l=None, v=None, u=None, dim=None, p=(None, None, None)):
            """Creates dict of fact value, unit, dimension, period tuple(type, start, end)"""
            _info_val_keys = ['label', 'value', 'unit', 'dimMemberLabel', 'period']
            _dict = dict(zip(_info_val_keys, [l, v, u, dim, p]))
            return _dict

        def modelXbrl_info(mXbrl: arelle.ModelXbrl.ModelXbrl, pos):
            """modelXbrl_info gets dei basic information form a modelXbrl"""
            dei_info = ['EntityRegistrantName', 'EntityCentralIndexKey',
                        'TradingSymbol', 'DocumentType', 'DocumentPeriodStartDate',
                        'CurrentFiscalYearEndDate', 'DocumentPeriodEndDate', 'DocumentFiscalPeriodFocus',
                        'DocumentFiscalYearFocus', 'EntityCommonStockSharesOutstanding',
                        'EntityPublicFloat', 'EntityListingParValuePerShare']
            info = OrderedDict()
            info['ModelXbrl at position'] = makeValDict(l='ModelXbrl at position', v=pos)
            for _c in dei_info:
                _c_enum = _c
                i = 1
                for _cx in mXbrl.nameConcepts[_c]:
                    _fcts = list(mXbrl.factsByQname[_cx.qname])
                    _fcts.sort(key=lambda z: z.sourceline)
                    for _f in _fcts:
                        _cntx = _f.context
                        _lbl = ''
                        if len(_cntx.qnameDims) > 0:
                            _cntx_ky = list(_cntx.qnameDims.keys())[0]
                            _lbl = _cntx.qnameDims[_cntx_ky].member.label()
                        _prdEnd = (
                            _cntx.endDatetime - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                        _cntx_dim_lbl = _lbl if _lbl else None
                        _ky = _cx.label()
                        while _c_enum in info.keys():
                        # if _ky in info.keys():
                            _ky = _cx.label() + ' ({})'.format(i)
                            _c_enum = _c + ' ({})'.format(i)
                            i += 1
                        _cntx_prd = ()
                        if _cntx.isForeverPeriod:
                            _cntx_prd = ('forever', None, None)
                        elif _cntx.isInstantPeriod:
                            _instprd = XmlUtil.dateunionValue(_cntx.instantDatetime, subtractOneDay=True)
                            _cntx_prd = ('instant', _instprd, None)
                        else:
                            _cntx_prd = (
                                'duration',
                                XmlUtil.dateunionValue(_cntx.startDatetime),
                                XmlUtil.dateunionValue(
                                    _cntx.endDatetime, subtractOneDay=True)
                            )
                        # info[_ky] = (_f.value, _cntx_dim_lbl)
                        _unt = _f.unit.value if _f.unit is not None else None
                        # info[_ky] = makeValDict(v=_f.value, u=_unt, dim=_cntx_dim_lbl,
                        #                         p=_cntx_prd)
                        info[_c_enum] = makeValDict(l=_ky, v=_f.value, u=_unt, dim=_cntx_dim_lbl,
                        p=_cntx_prd)
            info['Source File'] = makeValDict(l='Source File', v=mXbrl.uri)
            info['ModelXbrl'] = makeValDict(l='ModelXbrl', v=mXbrl)
            return info

        mXbrl = None
        if mdlXbrl:
            mXbrl = mdlXbrl
        else:
            mXbrl = self.modelManager.loadedModelXbrls
        mX_lst = chkToList(mXbrl, arelle.ModelXbrl.ModelXbrl)
        _positions = range(len(mX_lst))
        mX_info = list(map(modelXbrl_info, mX_lst, _positions))
        for d in mX_info:
            _lines = []
            for k in d:
                cntxt = ''
                _dim = ''
                if d[k]['dimMemberLabel']:
                    _dim = d[k]['dimMemberLabel']
                _cntxt_prd = ''
                _prdtyp = d[k]['period']
                if _prdtyp[0] == 'forever':
                    _cntxt_prd = ''
                elif _prdtyp[0] == 'instant':
                    _cntxt_prd = '{}'.format(_prdtyp[1])
                elif _prdtyp[0] == 'duration':
                    _cntxt_prd = 'from {} to {}'.format(_prdtyp[1], _prdtyp[2])
                if _dim and _cntxt_prd:
                    cntxt = '({} {})'.format(_dim, _cntxt_prd)
                elif _dim or _cntxt_prd:
                    cntxt = '({}{})'.format(_dim, _cntxt_prd)
                unt = ' ' + d[k]['unit'] if d[k]['unit'] else ''
                _ln = (d[k]['label'], '{}{} {}'.format(d[k]['value'], unt, cntxt).strip())
                _lines.append(_ln)
            d['Info'] = _lines
            if displayInfo:
                for _l in _lines:
                    print('{}: {}'.format(*_l).encode('utf-8'))
                    # print(_l[0] + b': ' + _l[1])
                print('---------------------------------')

        if not returnObj:
            mX_info = None
        return mX_info

class subProcessCntlrPy(CntlrPy):
    '''Helper to run in multiprocesses'''
    def __init__(self, instConfigDir, useResDir, hasGui=False, 
                 logFileName=None, logFileMode=None, logFileEncoding=None, logFormat=None, logLevel=None,
                 logHandler=None, logToBuffer=False, logTextMaxLength=None, logRefObjectProperties=True,
                 loadPlugins=True, loadPackages=False, preloadPlugins=None, q=None, logOrNot=True):
        self.uiQueue = q
        super().__init__(instConfigDir=instConfigDir, useResDir=useResDir, hasGui=hasGui, 
                         logFileName=logFileName, logFileMode=logFileMode, logFileEncoding=logFileEncoding, logFormat=logFormat, logLevel=logLevel,
                         logHandler=logHandler, logToBuffer=logToBuffer, logTextMaxLength=logTextMaxLength, logRefObjectProperties=logRefObjectProperties,
                         loadPlugins=loadPlugins, loadPackages=loadPackages, preloadPlugins=preloadPlugins)
    
    def showStatus(self, message, clearAfter=None):
        if self.uiQueue:
            self.uiQueue.put(('showStatus', [message, clearAfter]))
        else: 
            # super().showStatus(message, clearAfter)
            print(message)
    
    def addToLog(self, message, messageCode="arellepy.Info", messageArgs=None,  file="", refs=[],  level=logging.INFO):
        if self.uiQueue:
            self.uiQueue.put(('addToLog', [message, messageCode, messageArgs, file, refs, level]))
        else:
            # super().addToLog(message,messageCode,messageArgs,file, refs, level)
            pass

def renderEdgarReports(rssItem, saveToFolderPath, plugins=None, q=None):
    '''Creates Edegar report for SEC filings along with additional `additionalMeta.json` file (used by LocalViewerStandalone) 
    and saves output to selected folder, modelRssItem is meant to be the starting point of this process.
    args:  
        rssItem: modelRssItem
        saveToFolderPath: save rendered report to which folder (a sub folder will be created for the current instance)
        plugins: list of absolute paths to required plugins 'validate/EFM', 'EdgarRenderer','transforms/SEC'. None if using default plugins location of Arelle installation,
                the default is ['validate/EFM', 'EdgarRenderer','transforms/SEC']

    '''
    gettext.install('arelle') 
    # information from rssItem
    _cntlr = rssItem.modelDocument.modelXbrl.modelManager.cntlr
    instConfigDir = _cntlr.userAppDir
    useResDir = os.path.dirname(_cntlr.configDir)
    logFileName = 'logToBuffer'
    inlineXbrl = 0
    inlineAttrib = rssItem.xpath('.//@*[local-name()="inlineXBRL"]')
    if inlineAttrib:
        isInlineXbrl = inlineAttrib[0]
        if isinstance(isInlineXbrl, str):        
            if 't' in isInlineXbrl.lower():
                inlineXbrl = 1
            else:
                inlineXbrl = 0
        elif isinstance(isInlineXbrl, bool):
            int(isInlineXbrl)
    indexLink = rssItem.find('link').text
    primeDoc = rssItem.primaryDocumentURL
    filingDate = str(rssItem.filingDate)
    entryPointUrl = getattr(rssItem, 'url', None)
    errors  = []

    # Check if all required plugins exits
    requiredPlugins = ['validate/EFM','EdgarRenderer','transforms/SEC']
    if plugins:
        requiredPlugins = plugins

    chkPlugins = [os.path.isdir(x) if os.path.isabs(x) else os.path.isdir(os.path.join(useResDir, 'plugin', x)) for x in requiredPlugins]
    
    if not all(chkPlugins):
        raise Exception(_('Cannot find required plugin(s) {}'.format(', '.join([x for x,y in zip(requiredPlugins, chkPlugins) if not y]))))
    
    preloadPlugins = '|'.join(requiredPlugins)
    
    # create subfolder for the report
    reportFolder = os.path.join(saveToFolderPath, os.path.basename(entryPointUrl).replace('.', '_'))
 
    if os.path.isdir(reportFolder):
        files = os.listdir(reportFolder)
        if all([x in files for x in ["FilingSummary.xml","additionalMeta.json"]]):
            return reportFolder, errors
    else:
        os.makedirs(reportFolder)

    # initialize cntlr
    # c = CntlrPy(instConfigDir=instConfigDir, useResDir=useResDir, logFileName=logFileName,  preloadPlugins=preloadPlugins)
    c = subProcessCntlrPy(instConfigDir=instConfigDir, useResDir=useResDir, logFileName=logFileName,  preloadPlugins=preloadPlugins, q=q)
    # Run arelle to create the Edgar report pack
    retries =0
    badURL = True
    while badURL and retries <=3:
        c.runKwargs(file= entryPointUrl, logFile= logFileName, reports=reportFolder, 
                    disclosureSystem= 'efm-nonblocking', copyInlineFilesToOutput=True)
        if 'FileNotLoadable' in c.modelManager.modelXbrl.errors:
            c.modelManager.close()
            badURL = True
            if 'FileNotLoadable' not in errors:
                errors.append('FileNotLoadable')
            if os.path.exists(reportFolder) and os.path.isdir(reportFolder):
                shutil.rmtree(reportFolder)
            retries +=1
            c.showStatus(_('Retrying to process {} after errors {}'.format(entryPointUrl, ','.join(errors)))) 
        else:
            badURL = False
            errors = [] # clear errors

    if badURL:
        c.showStatus(_('{} not downloadable'.format(entryPointUrl)))
        return reportFolder, errors


    # Create a jason file containing information needed to be passed on to javascript for the viewer
    dei_info = ['EntityRegistrantName', 
                'EntityCentralIndexKey',
                'TradingSymbol', 
                'DocumentType', 
                'CurrentFiscalYearEndDate',
                'DocumentPeriodEndDate', 
                'DocumentFiscalPeriodFocus',
                'DocumentFiscalYearFocus', 
                'DocumentEffectiveDate']

    mX = c.modelManager.modelXbrl
    summary_dict = OrderedDict()
    for cpt in dei_info:
        for _cpt in mX.nameConcepts.get(cpt):
            _fcts = list(mX.factsByQname[_cpt.qname])
            if _fcts:
                _fcts.sort(key=lambda z: z.sourceline)
                fact = _fcts[0]
                res = [fact.concept.label(), fact.effectiveValue.strip()]
                summary_dict[cpt] = res
            else:
                summary_dict[cpt] = ['', '']

    summary_dict['Source File'] = ['Source File', os.path.join(reportFolder, os.path.basename(entryPointUrl))]
    card_dict = OrderedDict()
    tkr = " (" + summary_dict['TradingSymbol'][1] + \
        ")" if summary_dict['TradingSymbol'][1] else ''
    hdr = summary_dict['EntityRegistrantName'][1] + tkr
    card_dict["card-header"] = hdr
    card_dict["card-cik"] = summary_dict['EntityCentralIndexKey']
    card_dict["card-doctype"] = summary_dict['DocumentType']
    yearEnd = summary_dict['DocumentPeriodEndDate'][1]
    for fmt in ('%b. %d, %Y', '%B %d, %Y'):
        try:
            _yearEnd = datetime.datetime.strptime(yearEnd, fmt).date()
            yearEnd = _yearEnd
            break
        except ValueError:
            pass
    prdFocus = summary_dict['DocumentFiscalPeriodFocus'][1]
    yearFocus = summary_dict['DocumentFiscalYearFocus'][1]
    docDate = "{} {}{}{}{}{}".format(str(yearEnd), " (" if any([prdFocus, yearFocus]) else "",
                                prdFocus, "-" if all([prdFocus, yearFocus]) else "", yearFocus,
                                ")" if any([prdFocus, yearFocus]) else "" 
                                )
    card_dict["card-docEndDate"] = ["Report Date", docDate]
    card_dict["card-fyEnd"] = summary_dict['CurrentFiscalYearEndDate']
    card_dict["card-filingDate"] = ['Filing Date', str(filingDate)]
    card_dict["card-sourceFileLoc"] = summary_dict['Source File']
    is_inlineXbrl = 'Yes' if inlineXbrl else 'No'
    card_dict['card-inlineXbrl'] = ['Inline XBRL', is_inlineXbrl]
    card_dict['indexLink'] = ['Filing Link', indexLink]
    card_dict['primeDoc'] = ['Primary Document', '']
    primeDocName = os.path.basename(primeDoc)
    if not primeDocName in os.listdir(reportFolder):
        try:
            doc = request.urlopen(primeDoc)
            if doc.code == 200:
                with open(os.path.join(reportFolder, primeDocName), 'wb') as pDoc:
                    pDoc.write(doc.read())
                card_dict['primeDoc'] =  ['Primary Document', os.path.join(reportFolder, primeDocName)]
        except:
            c.showStatus(_('Could not get primary html document'))
    else:
        card_dict['primeDoc'] =  ['Primary Document', os.path.join(reportFolder, primeDocName)]


    card_dict["dataAttrs"] = [
        summary_dict["EntityCentralIndexKey"][1],
        summary_dict['DocumentType'][1],
        summary_dict['DocumentFiscalPeriodFocus'][1],
        summary_dict['DocumentFiscalYearFocus'][1],
        str(yearEnd),
        is_inlineXbrl, str(filingDate), primeDocName
    ]

    # make sure report in created
    url = "FilingSummary.xml"
    if os.path.exists(os.path.join(reportFolder, url)):
        # save additional meta 
        with open(os.path.join(reportFolder, 'additionalMeta.json'), 'w') as jF:
            json.dump(card_dict, jF)
    else:
        msg = _("{} was not found in {}".format(url, reportFolder))
        c.addToLog(msg, messageCode="arelle.Info", level=logging.INFO)
        c.showStatus(msg)
        return

    return reportFolder, errors

def renderEdgarReportsFromRssItems(mainCntlr, rssItems=None, saveToFolder=None, pluginsDirs=None):
    cntlr = mainCntlr
    if not len(rssItems):
        cntlr.addToLog(_('Param rssitems must be a list of ModelRssItem objects'), messageCode="arellepy.Error",  file="",  level=logging.ERROR)
        return
    startTime = time.perf_counter()
    pubDateRssItems = []
    _items = rssItems
    n = 0
    reportFolder = None
    for _rssItem in _items:
        pubDateRssItems.append((_rssItem.pubDate, _rssItem))
    for pubDate, rssItem in sorted(pubDateRssItems, reverse=True):
        res = []
        plugins = pluginsDirs
        try:
            rssItem.status = 'Render Edgar Reports'
            _start = time.perf_counter()
            reportFolder = renderEdgarReports(rssItem, saveToFolder, plugins, None)
            _end = time.perf_counter()
            res.append(reportFolder)
            rssItem.results = [reportFolder]
            cntlr.addToLog(_('Done rendering form {} for {} in {} secs').format(rssItem.formType, rssItem.companyName, round(_end-_start,3)), messageCode="arellepy.Info", level=logging.INFO)
            n +=1
        except Exception as e:
            cntlr.addToLog(_('Error in rendering form {} for {}\n{}').format(rssItem.formType, rssItem.companyName, str(e)), 
                            messageCode="arellepy.Error",  file=getattr(rssItem, 'url', None),  level=logging.ERROR)
            return
    endTime = time.perf_counter()
    cntlr.addToLog(_('Done with Rendering {} reports in {} secs').format(n,round(endTime-startTime,3)), messageCode="arellepy.Info", level=logging.INFO)
    
    return saveToFolder

def removeDuplicatesFromXmlDocument(modelXbrl):
    cntlr = modelXbrl.modelManager.cntlr
    # Remove duplicates from output
    if getattr(cntlr, 'rssDBFormulaRemoveDups', False):
        from arelle.ModelInstanceObject import ModelFact
        from arelle.ModelDtsObject import ModelObject
        try:
            f1 = [x for x in modelXbrl.modelDocument.xmlRootElement.iterchildren() if x.localName not in ('schemaRef', 'context', 'unit')]
            for obj in f1:
                if not hasattr(obj, 'isDuplicate'):
                    obj.isDuplicate = False
                if getattr(obj, 'isDuplicate'):
                    continue
                for OtherObj in f1:
                    if not hasattr(OtherObj, 'isDuplicate'):
                        OtherObj.isDuplicate = False
                    if getattr(OtherObj, 'isDuplicate'):
                        continue
                    if not obj is OtherObj:
                        if type(obj) is ModelFact and type(OtherObj) is ModelFact:
                            if OtherObj.isDuplicateOf(obj):
                                OtherObj.isDuplicate = True
                                cntlr.addToLog(_('Removing duplicate element "{}" from formula output').format(OtherObj.tag),
                                        messageCode="arellepy.Info",  file=modelXbrl.modelDocument.basename, refs=[{'href': OtherObj},], level=logging.INFO)
                                # cntlr.showStatus(_('Removing duplicate element "{}" from formula output').format(OtherObj.tag))
                                OtherObj.getparent().remove(OtherObj)
                        elif type(obj) is ModelObject and type(OtherObj) is ModelObject:
                            if obj.tag == OtherObj.tag and all([all([obj.attrib.get(att) == OtherObj.attrib.get(att) for att in obj.attrib.keys()]), obj.text.strip() == OtherObj.text.strip()]):
                                OtherObj.isDuplicate = True
                                cntlr.addToLog(_('Removing duplicate element "{}" from formula output').format(OtherObj.tag),
                                        messageCode="arellepy.Info",  file= modelXbrl.modelDocument.basename, refs=[{'href': OtherObj},], level=logging.INFO)
                                # cntlr.showStatus(_('Removing duplicate element "{}" from formula output').format(OtherObj.tag))
                                OtherObj.getparent().remove(OtherObj)
        except Exception as e:
            cntlr.addToLog(_('Error Removing Duplicates from "{}":\n{}').format(modelXbrl.modelDocument.basename, str(e)),
                                messageCode="arellepy.Info",  file=modelXbrl.modelDocument.basename,  level=logging.ERROR)
            cntlr.showStatus(_('Error Removing Duplicates from "{}":\n{}').format(modelXbrl.modelDocument.basename, str(e)))

def extractFormulaOutput(modelXbrl, formulaId=None, filingId=None, inlineXbrl=0):
    from arelle.ModelFormulaObject import ModelValueAssertion
    mx = modelXbrl
    outputRes = dict()
    # Get assertions result
    assertionsRes = [{x.xlinkLabel: {'SatisfiedCount': x.countSatisfied, 'NotSatisfiedCount': x.countNotSatisfied}}
                     for x in mx.modelVariableSets if type(x) is ModelValueAssertion]
    # Get output string:
    outputString = ''
    if mx.formulaOutputInstance:
        outputString = etree.tostring(mx.formulaOutputInstance.modelDocument.xmlRootElement).decode(
            mx.formulaOutputInstance.modelDocument.xmlDocument.docinfo.encoding)

    # result:
    outputRes = {'filingId': filingId,
                      'formulaId': formulaId,
                      'inlineXBRL': inlineXbrl,
                      'formulaOutput': outputString,
                      'assertionsResults': json.dumps(assertionsRes) if assertionsRes else None,
                      'dateTimeProcessed': datetime.datetime.now().replace(microsecond=0),
                      'processingLog': modelXbrl.modelManager.cntlr.logHandler.getXml().replace('\n', '')}
    return outputRes

def makeFormulaDict(formulaString=None, formulaSourceFile=None, writeFormulaToSourceFile=False, formulaId=None, tempDir=None):
    '''Returns formula dict ready to run or insert into DB, source can be from xml string or file.

    This function is used as an intermidiate step before running the formula, the source can be:
    - formula entry extracted from db, the destination is running the formula as an imported file with the instance document.
    - formula generated by whatever means, the destination can be running the formula as an imported file with the instance document or the
    destination can be adding formula to the DB.

    At least one of `formulaString` or formulaSourceFile (valid formula linkbase) must be entered, if both are entered and `writeFormulaToSourceFile`
    is `True`, the `formulaString` will be written back to the `formulaSourceFile` and if `writeFormulaToSourceFile` is False the `formulaString` will 
    be used and `formulaSourceFile` ignored but reported as name of formula file, if only `formulaString` is entered then the formula will be saved to 
    a temp file in `tempDir`, and will disappear on exit unless the result is inserted into rssDB.

    formulaId is the desired Id to be given to this formula, should not conflict with other ids in the DB, if left None, an id will be assigned when
    inserting into db.
    '''
    if formulaString is None and formulaSourceFile is None:
        raise Exception('At least one of formulaString or formulaSourceFile must be entered')

    if writeFormulaToSourceFile and formulaString and formulaSourceFile is None:
        raise Exception(_('No file provided to write formula'))
    
    inputFile = None
    if formulaString is None and formulaSourceFile:
        inputFile = formulaSourceFile
        formulaString = etree.tostring(etree.parse(inputFile))
    elif (formulaString and formulaSourceFile is None) or (formulaString and formulaSourceFile and not writeFormulaToSourceFile):
        _inputFile = xmlFileFromString(xmlString=formulaString, filePrefix='rssDB_formula_', identifier=formulaId, tempDir=tempDir, deleteF=False)
        inputFile = _inputFile.name
    elif writeFormulaToSourceFile and formulaString and formulaSourceFile:
        with open(formulaSourceFile, 'wb') as ff:
            ff.write(formulaString if type(formulaString) is bytes else bytes(formulaString, encoding='utf-8'))
        _inputFile = xmlFileFromString(xmlString=formulaString, temp=False, filepath=formulaSourceFile)
        inputFile = _inputFile.name

    if not formulaSourceFile:
        formulaSourceFile = inputFile
    
    formulaDict = {'formulaId': formulaId, 'fileName':formulaSourceFile, 'formulaLinkbase': formulaString, 'inputFile':inputFile}

    return formulaDict

def runFormulaHelper(argsDict, q):
    res = False
    url = argsDict['url']
    b = CntlrPy(instConfigDir=argsDict['configDir'], useResDir=argsDict['resDir'], logFileName="logToBuffer")
    n=0
    badUrl = True
    errors = set()
    while badUrl and n<=3:
        errorResult=None
        try:
            b.runKwargs(file= url[1], logFile= 'logToBuffer', validate=True, imports= argsDict['inputFile'], rssDBFormulaRemoveDups=True, plugins='-Edgar Renderer')
        except Exception as e:
            _msg = 'Something went wrong while processing {}:\n{}'.format(url[1], str(e)) 
            errorResult = {'filingId': url[0],
                        'formulaId': argsDict['formulaId'],
                        'inlineXBRL': url[2] if url[2] else 0,
                        'formulaOutput': '',
                        'assertionsResults': '',
                        'dateTimeProcessed': datetime.datetime.now().replace(microsecond=0),
                        'processingLog': _msg,
                        'errors': _msg}
            b.showStatus(_msg)
            b.modelManager.close()
            res = False
        if n == 3 and errorResult:
            q.put(errorResult)
        if 'FileNotLoadable' in b.modelManager.modelXbrl.errors:
            res= False
            badUrl = True
            n +=1
            for e in b.modelManager.modelXbrl.errors:
                errors.add(e)
            b.modelManager.close()
            b.showStatus(_('Retrying to process {} after errors {}'.format(url[1], ','.join(errors))))
        else:
            res = True
            badUrl = False
            q.put(extractFormulaOutput(b.modelManager.modelXbrl, formulaId=argsDict['formulaId'], filingId=url[0], inlineXbrl=url[2] if url[2] else 0))
    b.modelManager.close()
    b.close()
    return res

def runFormulaFromDBonRssItems(conn, rssItems, formulaId, additionalImports=None, insertResultIntoDb=False, updateExistingResults=False, saveResultsToFolder=False, folderPath=None, returnResults=True):
    '''Runs formula with id `formulaId` on selected rssItems
    
    rssItems are checked against db formulaeResults table to see if an entry exist for the same formula applied to those filings, if `updateExistingResults` is set
    to False, formula will not be applied again to the same filings, if set to True, formula will be applied again. 
    
    To touch db (insert or update) `insertResultIntoDb` must be set to True, this will trigger updating db existing formula results for same filings and inserting
    new results to db, if `insertResultIntoDb` is set to False, formula will be ran and result returned within the return dict with key "output".

    To make sure to apply formula to ALL selected filings (even if applied before and stored in db), set `updateExistingResults` to True. 
    
    Formula output can be saved to files if `saveResultsToFolder` is set to True, but a valid path to a folder to save the files to must be set by `folderPath`.

    insertResultIntoDb = True AND updateExistingResults= True : process ALL filings and inserts/updates db
    insertResultIntoDb = True AND updateExistingResults= False : process filings NOT previously processed with this formula and inserts into db
    insertResultIntoDb = False AND updateExistingResults= True : process ALL filings

    Returns a dict containing formula outputs, formula information, ids of new filings processed, ids of existing filings processed, stats, errors.
    '''
    # get formula by id
    startTime = time.perf_counter()
    cntlr = conn.cntlr
    configDir = cntlr.userAppDir
    resDir = os.path.dirname(cntlr.configDir)
    formulaDict= dict()
    inputRes = dict()
    outputRes = dict()
    finalRes = dict()
    errors = defaultdict(list)
    newKeys = []
    existingKeys = []
    urlsToProcess = []
    stats = []

    if formulaId is None or not isinstance(formulaId, int):
        cntlr.addToLog(_('A valid formulaId must be selected to run'), messageCode="arellepy.Error", file=conn.conParams['database'], level=logging.ERROR)
        return

    if rssItems is None or len(rssItems)==0:
        cntlr.addToLog(_('Filings must be selected to run'), messageCode="arellepy.Error", file=conn.conParams['database'], level=logging.ERROR)
        return

    if saveResultsToFolder and not folderPath:
        cntlr.addToLog(_('folderPath must be a valid path to a dir to save formulae output to files'), messageCode="arellepy.Error", 
                            file=conn.conParams.get('database', ''),  level=logging.ERROR)
        return        
    
    qryRes = conn.getById([formulaId], 'formulae', 'formulaId', int)
    
    if qryRes:
        formulaDict = qryRes[0]
    else:
        cntlr.addToLog(_('No formula with formulaId {} was found in db').format(formulaId), messageCode="arellepy.Info", 
                             file=conn.conParams.get('database',''),  level=logging.INFO)
        return

    if formulaDict:
        # make sure we have XBRL or Extracted XBRL to be able to run the formula
        urls = []
        for x in rssItems:
            f_id = int(x.filingId) if hasattr(x, 'filingId') else int(x.find('filingId').text)
            f_inlineXbrl = 1 if x.find('isInlineXBRL').text=='true' else 0
            cntlr.addToLog(_('Getting url for filing id {}').format(f_id), messageCode="arellepy.Info", file=conn.conParams['database'], level=logging.INFO)
            f_url = getExtractedXbrlInstance(x) if x.find('isInlineXBRL').text=='true' else x.url
            urls.append((f_id, f_url, f_inlineXbrl, x))
        
        inputRes = makeFormulaDict(formulaString=formulaDict.get('formulaLinkbase', None), formulaSourceFile=formulaDict.get('fileName', None), 
                                    writeFormulaToSourceFile=False, formulaId=formulaDict.get('formulaId', None), tempDir=conn.cntlr.userAppTempDir)
        if inputRes['inputFile']:
            inputRes['inputFile'] = inputRes['inputFile'] + '|' + additionalImports if additionalImports else ''


        _urls =  chkToList(urls, tuple, lambda x: len(x)==4)

        # Check if results for filingIds with the given formulaId exists before running the formula
        urlsDict = {(x[0], formulaId): x for x in _urls}
        keys = urlsDict.keys()

        whereClause = ''
        if conn.product in ('sqlite', 'postgres'):
            whereClause = ' OR '.join(['("filingId"={0} AND "formulaId"={1})'.format(x,y) for x,y in keys])
            # dateTimeProcessed could be useful to retrive and compare to formula dateTimeAdded
            db = conn.execute('SELECT "filingId", "formulaId" from "formulaeResults" WHERE {}'.format(whereClause), fetch=True)
            _db = [tuple(x) for x in db]
            newKeys = [x for x in keys if x not in _db]
            existingKeys = [x for x in _db if x in keys]
        elif conn.product == 'mongodb':
            whereClause ={"$or": [{"$and": [{"filingId": x}, {"formulaId":y}]} for x,y in keys]}
            db = [(x['filingId'], x['formulaId']) for x in conn.dbConn.formulaeResults.find(whereClause, {"_id":0, "filingId":1, "formulaId":1})]
            _db = [tuple(x) for x in db]
            newKeys = [x for x in keys if x not in _db]
            existingKeys = [x for x in _db if x in keys]

        if updateExistingResults:
            urlsToProcess=keys
            if existingKeys:
                cntlr.addToLog(_('Entries for filingId(s) {} previously processed by formulaId "{}" will be processed again and updated in db').format(str([x[0] for x in existingKeys]), 
                                    formulaId), messageCode="arellepy.Info",  file=conn.conParams.get('database', ''),  level=logging.INFO)
        else:
            urlsToProcess=newKeys
            if existingKeys:
                cntlr.addToLog(_('Entries for filingId(s) {} previously processed by formulaId "{}" will NOT be processed').format(str([x[0] for x in existingKeys]), 
                                    formulaId), messageCode="arellepy.Info",  file=conn.conParams.get('database', ''),  level=logging.INFO)

        manager = None
        q = None
        if sys.platform.lower().startswith('lin'):
            # Runs are processed in sequence, multiprocessing is used just to get rid of lxml leftovers in the subprocess
            manager = multiprocessing.Manager()
            q = manager.Queue()

        for _k in urlsToProcess:
            url = urlsDict[_k]
            _rssItem = url[-1]
            if sys.platform.lower().startswith('lin') and manager and q:
                try:
                    # Do not need to load plugins, using same parent Plugin Manager
                    argsDict = {'url': url, 'configDir': configDir, 'resDir': resDir, 'inputFile': inputRes['inputFile'], 'formulaId': inputRes['formulaId']}
                    p = multiprocessing.Process(target=runFormulaHelper, args=(argsDict, q), daemon=True)
                    # Update item stat if in GUI
                    if conn.cntlr.hasGui:
                        _rssItem.status = 'Run Formula {}'.format(formulaId)
                        conn.cntlr.modelManager.viewModelObject(_rssItem.modelXbrl, _rssItem.objectId())
                    p.start()
                    p.join()
                    outputRes[_k] = q.get()
                    if outputRes[_k].get('errors', False):
                        errors['formulaProcessing'].append((_k, outputRes[_k].get('errors', False)))
                        cntlr.addToLog(_('Processing formulaId "{}" with filingId "{}" caused error:\n {}').format( _k[1], _k[0],outputRes[_k].get('errors', '')), 
                                            messageCode="arellepy.Error", file=conn.conParams.get('database', ''),  level=logging.ERROR)
                    if conn.cntlr.hasGui:
                        _rssItem.results = ['Formula {} processed'.format(formulaId)]
                        conn.cntlr.modelManager.viewModelObject(_rssItem.modelXbrl, _rssItem.objectId())

                except Exception as e:
                    errors['formulaProcessing'].append((_k, e))
                    cntlr.addToLog(_('Processing formulaId "{}" with filingId "{}" caused error:\n {}').format(_k[1], _k[0], str(e)), 
                                        messageCode="arellepy.Error", file=conn.conParams.get('database', ''),  level=logging.ERROR)
            else:
                # for windows
                try:
                    # Update item stat if in GUI
                    if conn.cntlr.hasGui:
                        _rssItem.status = 'Run Formula {}'.format(formulaId)
                        conn.cntlr.modelManager.viewModelObject(_rssItem.modelXbrl, _rssItem.objectId())
                    # Do not need to load plugins, using same parent Plugin Manager
                    b = CntlrPy(instConfigDir=configDir, useResDir=resDir, logFileName="logToBuffer")
                    b.runKwargs(file= url[1], logFile= 'logToBuffer', validate=True, imports= inputRes['inputFile'], rssDBFormulaRemoveDups=True)
                    outputRes[(url[0], formulaId)] = extractFormulaOutput(b.modelManager.modelXbrl, formulaId=formulaId, filingId=url[0], 
                                                                            inlineXbrl=url[2] if url[2] else 0)
                    b.modelManager.close()
                    if conn.cntlr.hasGui:
                        _rssItem.results = ['Formula {} processed'.format(formulaId)]
                        conn.cntlr.modelManager.viewModelObject(_rssItem.modelXbrl, _rssItem.objectId())
                except Exception as e:
                    errors['formulaProcessing'].append((_k, e))
                    cntlr.addToLog(_('Processing formulaId "{}" with filingId "{}" caused error:\n {}').format(_k[1], _k[0], str(e)), 
                                        messageCode="arellepy.Info",  file=conn.conParams.get('database', ''),  level=logging.INFO)

            # insert/update DB (insert as completed so not to lose everything one something goes wrong)
            if insertResultIntoDb:
                if _k in newKeys:
                    try:
                        gettext.install('arelle')
                        _s = conn.insertUpdateRssDB([outputRes[_k]], 'formulaeResults', action='insert', commit=True, returnStat=True)
                        stats.append(_s)
                    except Exception as e:
                        errors['dbInsert'].append(e)

            if updateExistingResults and insertResultIntoDb:
                if _k in existingKeys:
                    try:
                        gettext.install('arelle')
                        _s = conn.insertUpdateRssDB([outputRes[_k]], 'formulaeResults', 'update', None, ['filingId','formulaId'], commit=True, returnStat=True)
                        stats.append(_s)
                    except Exception as e:
                        errors['dbUpdate'].append(e)

            if saveResultsToFolder:
                if folderPath:
                    if not os.path.isdir(folderPath):
                        os.mkdir(folderPath)

                    k = _k
                    src = outputRes[_k]
                    try:
                        fileName = 'rssDBFormula_'
                        fileName += 'formulaId_{}_'.format(str(src.get('formulaId',False))) if src.get('formulaId',False) else ''
                        fileName += 'filingId_{}_'.format(str(src.get('filingId',False))).replace('.','_') if src.get('filingId',False) else '' 
                        fileName += 'on_{}.xml'.format(datetime.datetime.now().strftime("%Y%m%d%H%M"))
                        filePath = os.path.join(folderPath, fileName)
                        cntlr.addToLog(_('Saving formula output for filing {} to {}').format(k[0], filePath), messageCode="arellepy.Info", 
                                         file=conn.conParams.get('database', ''),  level=logging.INFO)
                        fHandle = xmlFileFromString(src['formulaOutput'], temp=False, filepath=filePath)
                        fHandle.seek(0)
                        fHandle.close()
                    except Exception as e:
                        errors['saveFiles'].append(e)
                        cntlr.addToLog(_('Error saving formula output for filingId {}, formulaId {}: {}').format(k[0], k[1], str(e)), 
                                            messageCode="arellepy.Error",  file=conn.conParams.get('database', ''),  level=logging.ERROR)
                else:
                    errors['saveFiles'].append('No folderPath entered')
                    cntlr.addToLog(_('folderPath must be a valid path to a dir to save formulae output to files'), messageCode="arellepy.Error", 
                                        file=conn.conParams.get('database', ''),  level=logging.ERROR)
    if returnResults:
        finalRes = {'output':outputRes, 'input': inputRes, 'update': existingKeys, 'insert':newKeys, 'stats':stats, 'errors':errors}

    endTime = time.perf_counter()
    allTime = str(round(endTime - startTime, 3)) + ' sec(s)'
    countFilings = 'on ' + str(len(outputRes)) + ' filings' if len(outputRes) else ''
    countErrors = sum([len(x) for x in errors.values()])
    countInserts = sum([x.get('insert', 0) for x in stats])            
    countUpdates = sum([x.get('update', 0) for x in stats])            
    cntlr.addToLog(_('Finished runing formula {} in {} with {} errors,'
                     '{} db inserts, {} db updates').format(countFilings, allTime, countErrors, countInserts, countUpdates), 
                     messageCode="arellepy.Info",  file=conn.conParams.get('database', ''),  level=logging.INFO)

    return finalRes

def runFormula(cntlr, instancesUrls, formulaString=None, formulaSourceFile=None, formulaId=None, writeFormulaToSourceFile=False, 
               saveResultsToFolder=False, folderPath=None):
    '''Runs formula from string or file on list of instances urls or rssItems WITHOUT depending on DB

    `instancesUrls` ideally a list of XBRL (.xml) documents, if inlineXBRL is in the list, tries to guess the url of the extracted XBRL instance and use it.

    At least one of `formulaString` or formulaSourceFile (valid formula linkbase) must be entered, if both are entered and `writeFormulaToSourceFile`
    is `True`, the `formulaString` will be written back to the `formulaSourceFile` and if `writeFormulaToSourceFile` is False the `formulaString` will 
    be used and `formulaSourceFile` ignored but reported as name of formula file, if only `formulaString` is entered then the formula will be saved to 
    a temp file, and will disappear on exit unless the result is inserted into rssDB. formulaId can be whatever identifier given to this formula, it will
    be used for file name if `saveResultsToFolder` is chosen.
    
    Formula output can be saved to files if `saveResultsToFolder` is set to True, but a valid path to a folder to save the files to must be set by `folderPath`.

    Returns a dict containing formula outputs, formula information, ids of new filings processed, ids of existing filings processed, stats, errors.
    '''
    # get formula by id
    if not formulaId:
        formulaId = '0000'
    startTime = time.perf_counter()
    configDir = cntlr.userAppDir
    resDir = os.path.dirname(cntlr.configDir)
    inputRes = dict()
    outputRes = dict()
    finalRes = dict()
    errors = defaultdict(list)
    urlsToProcess = []

    #prep formula
    inputRes = makeFormulaDict(formulaString=formulaString, formulaSourceFile=formulaSourceFile, 
                                writeFormulaToSourceFile=writeFormulaToSourceFile, formulaId=formulaId, tempDir=cntlr.userAppTempDir)

    # make tuples for urls (fileName, url, inlineXBRL)
    # make sure we have XBRL or Extracted XBRL to be able to run the formula
    from arelle.ModelRssItem import ModelRssItem
    
    if inputRes:
        urls = []
        for x in instancesUrls:
            if type(x) is ModelRssItem:
                f_id = int(x.filingId) if hasattr(x, 'filingId') else int(x.find('filingId').text)
                f_inlineXbrl = 1 if x.find('isInlineXBRL').text=='true' else 0
                cntlr.addToLog(_('Getting url for filing id {}').format(f_id), messageCode="arellepy.Info", file='', level=logging.INFO)
                f_url = getExtractedXbrlInstance(x) if x.find('isInlineXBRL').text=='true' else x.url
                urls.append((f_id, f_url, f_inlineXbrl))
            else:
                f_id = os.path.basename(x)
                f_inlineXbrl = 1 if x.lower().endswith('.htm') else 0
                cntlr.addToLog(_('Getting url for filing id {}').format(f_id), messageCode="arellepy.Info", file='', level=logging.INFO)
                f_url = getExtractedXbrlInstance(x) if f_inlineXbrl else x
                urls.append((f_id, f_url, f_inlineXbrl))


        _urls =  chkToList(urls, tuple, lambda x: len(x)==3)
        urlsToProcess = [(x[0], formulaId) for x in _urls]
        if not urlsToProcess:
            cntlr.addToLog(_('No valid instances urls to process'), messageCode="arellepy.Info", file='', level=logging.INFO)
            return

        urlsDict = {(x[0], formulaId): x for x in _urls}

        manager = None
        q = None
        if sys.platform.lower().startswith('lin'):
            # Runs are processed in sequence, multiprocessing is used just to get rid of lxml leftovers in the subprocess
            manager = multiprocessing.Manager()
            q = manager.Queue()

        for _k in urlsToProcess:
            url = urlsDict[_k]
            if sys.platform.lower().startswith('lin') and manager and q:
                try:
                    # Do not need to load plugins, using same parent Plugin Manager
                    argsDict = {'url': url, 'configDir': configDir, 'resDir': resDir, 'inputFile': inputRes['inputFile'], 'formulaId': inputRes['formulaId']}
                    p = multiprocessing.Process(target=runFormulaHelper, args=(argsDict, q), daemon=True)
                    p.start()
                    p.join()
                    outputRes[_k] = q.get()
                    if outputRes[_k].get('errors', False):
                        errors['formulaProcessing'].append((_k, outputRes[_k].get('errors', False)))
                        cntlr.addToLog(_('Processing formulaId "{}" with filingId "{}" caused error:\n {}').format(_k[1], _k[0],outputRes[_k].get('errors', '')), 
                                            messageCode="arellepy.Error", file=url[0], level=logging.ERROR)
                except Exception as e:
                    errors['formulaProcessing'].append((_k, e))
                    cntlr.addToLog(_('Processing formulaId "{}" with filingId "{}" caused error:\n {}').format(_k[1], _k[0], str(e)), 
                                        messageCode="arellepy.Error", file=url[0], level=logging.ERROR)
            else:
                # for windows
                try:
                    # Do not need to load plugins, using same parent Plugin Manager
                    b = CntlrPy(instConfigDir=configDir, useResDir=resDir, logFileName="logToBuffer")
                    b.runKwargs(file= url[1], logFile= 'logToBuffer', validate=True, imports= inputRes['inputFile'], rssDBFormulaRemoveDups=True)
                    outputRes[(url[0], formulaId)] = extractFormulaOutput(b.modelManager.modelXbrl, formulaId=formulaId, filingId=url[0], 
                                                                            inlineXbrl=url[2] if url[2] else 0)
                    b.modelManager.close()
                except Exception as e:
                    errors['formulaProcessing'].append((_k, e))
                    cntlr.addToLog(_('Processing formulaId "{}" with filingId "{}" caused error:\n {}').format(_k[1], _k[0], str(e)), 
                                        messageCode="arellepy.Info",  level=logging.INFO)
    
            if saveResultsToFolder:
                if folderPath:
                    if not os.path.isdir(folderPath):
                        os.mkdir(folderPath)

                    k = _k
                    src = outputRes[_k]
                    try:
                        fileName = 'rssDBFormula_'
                        fileName += 'formulaId_{}_'.format(str(src.get('formulaId',False))) if src.get('formulaId',False) else ''
                        fileName += 'filingId_{}_'.format(str(src.get('filingId',False))).replace('.','_') if src.get('filingId',False) else '' 
                        fileName += 'on_{}.xml'.format(datetime.datetime.now().strftime("%Y%m%d%H%M"))
                        filePath = os.path.join(folderPath, fileName)
                        cntlr.addToLog(_('Saving formula output for filing {} to {}').format(k[0], filePath), messageCode="arellepy.Info", 
                                         level=logging.INFO)
                        fHandle = xmlFileFromString(src['formulaOutput'], temp=False, filepath=filePath)
                        fHandle.seek(0)
                        fHandle.close()
                    except Exception as e:
                        errors['saveFiles'].append(e)
                        cntlr.addToLog(_('Error saving formula output for filingId {}, formulaId {}: {}').format(k[0], k[1], str(e)), 
                                            messageCode="arellepy.Error",  level=logging.ERROR)
                else:
                    errors['saveFiles'].append('No folderPath given')
                    cntlr.addToLog(_('folderPath must be a valid path to a dir to save formulae output to files'), messageCode="arellepy.Error",  level=logging.ERROR)

    finalRes = {'output':outputRes, 'input': inputRes, 'errors':errors}

    endTime = time.perf_counter()
    allTime = str(round(endTime - startTime, 3)) + ' sec(s)'
    countFilings = 'on ' + str(len(outputRes)) + ' filings' if len(outputRes) else ''
    countErrors = sum([len(x) for x in errors.values()])           
    cntlr.addToLog(_('Finished runing formula {} in {} with {} errors').format(countFilings, allTime, countErrors), messageCode="arellepy.Info", 
                     level=logging.INFO)            

    return finalRes
