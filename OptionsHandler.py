'''Class to translate options between CntlrPy and CntlrCmdLine
'''


from collections import OrderedDict
import re
import gettext, time, os, sys, logging
from re import error
from optparse import OptionParser, SUPPRESS_HELP
from arelle import Cntlr, Version, ModelManager
from arelle import PluginManager
from arelle.PluginManager import pluginClassMethods
# from arelle.CntlrCmdLine import CntlrCmdLine
# from arellepy.CntlrPy import CntlrPy
from lxml import etree
win32file = win32api = win32process = pywintypes = None
STILL_ACTIVE = 259 # MS Windows process status constants
PROCESS_QUERY_INFORMATION = 0x400
RESERVED_KWARGS = {'import': 'imports'}

class OptionParser(OptionParser):
    def exit(self, status=0, msg=None):
        if msg:
            sys.stderr.write(msg)
            raise Exception(msg)
        return

class OptionsHandler:
    def __init__(self, cntlr, preloadPlugins=None):
        try:
            from arelle import webserver
            self.hasWebServer = True
        except ImportError:
            self.hasWebServer = False
        self.cntlr = cntlr
        parserObjects = self.makeParser(preloadPlugins=preloadPlugins)
        self.parser = parserObjects[0]
        self.pluginRef = parserObjects[1]
        self.pluginOptionsIndex = parserObjects[2]
        self.pluginLastOptionIndex = parserObjects[3]
        self.optsDict = self.makeOptsDict()
        self.kwargsDict = self.makeOptsDict(useKwargs=True)

    def makeOptsDict(self, useKwargs=False):
        startPattern = re.compile('^--')
        OptsDict = OrderedDict()
        allOpts = self.parser.option_list[:]
        allOpts.extend([y for x in self.parser.option_groups for y in x.option_list])
        for i, o in enumerate(allOpts):
            oDict = OrderedDict()
            _src = [x[0] for x in self.pluginRef if i >= x[1] and i < x[2]]
            source = _src[0] if _src else 'CntlrCmdLine'
            optStr = o.get_opt_string()
            if useKwargs:
                _kw = startPattern.sub('', optStr)
                optStr = _kw.replace('-', '_')
                if RESERVED_KWARGS.get(optStr, None):
                    optStr = RESERVED_KWARGS.get(optStr, None)
            if optStr:
                oDict['id'] = [i]
                oDict['src'] = source
                oDict['opt'] = o
                try:
                    _indx = [k.casefold() for k in OptsDict].index(optStr.casefold())
                    list(OptsDict.items())[_indx][1]['id'].append(i)
                except ValueError:
                    OptsDict[optStr] = oDict
        return(OptsDict)

    def dictOptsBySrc(self, show=True, srcOnly=False, returnDict=False):
        optbysrc = OrderedDict()
        for v in self.optsDict.values():
            if not v['src'] in optbysrc.keys():
                optbysrc[v['src']] = []
        for s in optbysrc:
            for k, v in self.optsDict.items():
                if v['src'] == s:
                    optbysrc[s].append(k)
        if show and not srcOnly:
            for k, v in optbysrc.items():
                print(k)
                if not srcOnly:
                    for o in v:
                        print('\t'+ o)
        elif show and srcOnly:
            for k, v in optbysrc.items():
                print(k)
        res = optbysrc
        if srcOnly:
            res = list(optbysrc.keys())
        if returnDict:
            return res

    def kwargsBySrc(self, show=True, srcOnly=False, returnDict=False, withHelp=False):
        '''Prints out available keywords arguments and crossponding command line options'''
        startPattern = re.compile('^--')
        optbysrc = OrderedDict()
        for v in self.optsDict.values():
            if not v['src'] in optbysrc.keys():
                optbysrc[v['src']] = []
        for s in optbysrc:
            for k, v in self.optsDict.items():
                if v['src'] == s:
                    _kw = startPattern.sub('', k)
                    kw = _kw.replace('-', '_')
                    if RESERVED_KWARGS.get(kw, None):
                        kw = RESERVED_KWARGS.get(kw, None)
                    optbysrc[s].append({'kw':kw, 'opt':v['opt']})
        if show and not srcOnly:
            for k, v in optbysrc.items():
                print(k)
                if not srcOnly:
                    for o in v:
                        # print('\t'+ o['kw'])
                        print('\t{} ==> {}'.format(o['kw'] , o['opt'])  )
                        if withHelp:
                            print('\t\t' + o['opt'].help)
        elif show and srcOnly:
            for k, v in optbysrc.items():
                print(k)
        res = optbysrc
        if srcOnly:
            res = list(optbysrc.keys())
        if returnDict:
            return res


    def optHelp(self, opt=None, returnDoc=False, searchRE=None, show=True):
        def helpText(k, v, p, r, s):
            startPattern = re.compile('^--')
            allOpts = p.option_list[:]
            allOpts.extend([y for x in p.option_groups for y in x.option_list])
            _kw = startPattern.sub('', k)
            kw = _kw.replace('-', '_')
            if RESERVED_KWARGS.get(kw, None):
                kw = RESERVED_KWARGS.get(kw, None)
            optName ='{} (kwarg={}): '.format(k, kw)
            src = '(Source - {})'.format(v['src'])
            txt = ''
            action = []
            dests = []
            for i in v['id']:
                hlp = allOpts[i].help
                if not hlp == 'SUPPRESSHELP':
                    txt += hlp
                action.append(allOpts[i].action)
                if allOpts[i].dest:
                    dests.append( allOpts[i].dest)
            lines = [optName + src, txt, 'action: '+ str(set(action)), 'dest: ' + str(set(dests))]
            doc = '\n'.join(lines)
            if s:
                print(doc + '\n' + '--------------')
            if r:
                return doc

        d = []
        if opt:
            try:
                d.append(helpText(opt, self.optsDict[opt], self.parser, returnDoc,show))
            except KeyError:
                print('{} Not Found'.format(opt))
                return
        if searchRE:
            pattern = re.compile(searchRE, flags=re.IGNORECASE)
            print('\nSearch Items:\n--------------')
            for k, v in self.optsDict.items():
                _d = helpText(k, v, self.parser, r=True, s=False)
                if pattern.findall(_d):
                    d.append(_d)
                    print(_d + '\n' +'-------------')
        if not opt and not searchRE:
            for k, v in self.optsDict.items():
                d.append(helpText(k, v, self.parser, returnDoc, show))
        if returnDoc:
            return d

    def makeParser(self, preloadPlugins=None):
        """Create parser to help runing CmdLineCntlr interactively, plugins managed by cntlr
        """
        gettext.install('arelle')

        hasWebServer = self.hasWebServer

        # try:
        #     from arelle import webserver
        #     hasWebServer = True
        # except ImportError:
        #     hasWebServer = False
        # cntlr = CntlrCmdLine()  # need controller for plug ins to be loaded
        cntlr = self.cntlr

        usage = "usage: %prog [options]"
        
        parser = OptionParser(usage, 
                            version="Arelle(r) {0} ({1}bit)".format(Version.__version__, cntlr.systemWordSize),
                            conflict_handler="resolve") # allow reloading plug-in options without errors
        parser.add_option("-f", "--file", dest="entrypointFile",
                        help=_("FILENAME is an entry point, which may be "
                                "an XBRL instance, schema, linkbase file, "
                                "inline XBRL instance, testcase file, "
                                "testcase index file.  FILENAME may be "
                                "a local file or a URI to a web located file.  "
                                "For multiple instance filings may be | separated file names or JSON list "
                                "of file/parameter dicts [{\"file\":\"filepath\"}, {\"file\":\"file2path\"} ...]."))
        parser.add_option("--username", dest="username",
                        help=_("user name if needed (with password) for web file retrieval"))
        parser.add_option("--password", dest="password",
                        help=_("password if needed (with user name) for web retrieval"))
        # special option for web interfaces to suppress closing an opened modelXbrl
        parser.add_option("--keepOpen", dest="keepOpen", action="store_true", help=SUPPRESS_HELP)
        parser.add_option("-i", "--import", dest="importFiles",
                        help=_("FILENAME is a list of files to import to the DTS, such as "
                                "additional formula or label linkbases.  "
                                "Multiple file names are separated by a '|' character. "))
        parser.add_option("-d", "--diff", dest="diffFile",
                        help=_("FILENAME is a second entry point when "
                                "comparing (diffing) two DTSes producing a versioning report."))
        parser.add_option("-r", "--report", dest="versReportFile",
                        help=_("FILENAME is the filename to save as the versioning report."))
        parser.add_option("-v", "--validate",
                        action="store_true", dest="validate",
                        help=_("Validate the file according to the entry "
                                "file type.  If an XBRL file, it is validated "
                                "according to XBRL validation 2.1, calculation linkbase validation "
                                "if either --calcDecimals or --calcPrecision are specified, and "
                                "SEC EDGAR Filing Manual (if --efm selected) or Global Filer Manual "
                                "disclosure system validation (if --gfm=XXX selected). "
                                "If a test suite or testcase, the test case variations "
                                "are individually so validated. "
                                "If formulae are present they will be validated and run unless --formula=none is specified. "
                                ))
        parser.add_option("--calcDecimals", action="store_true", dest="calcDecimals",
                        help=_("Specify calculation linkbase validation inferring decimals."))
        parser.add_option("--calcdecimals", action="store_true", dest="calcDecimals", help=SUPPRESS_HELP)
        parser.add_option("--calcPrecision", action="store_true", dest="calcPrecision",
                        help=_("Specify calculation linkbase validation inferring precision."))
        parser.add_option("--calcprecision", action="store_true", dest="calcPrecision", help=SUPPRESS_HELP)
        parser.add_option("--calcDeduplicate", action="store_true", dest="calcDeduplicate",
                        help=_("Specify de-duplication of consistent facts when performing calculation validation, chooses most accurate fact."))
        parser.add_option("--calcdeduplicate", action="store_true", dest="calcDeduplicate", help=SUPPRESS_HELP)
        parser.add_option("--efm", action="store_true", dest="validateEFM",
                        help=_("Select Edgar Filer Manual (U.S. SEC) disclosure system validation (strict)."))
        parser.add_option("--gfm", action="store", dest="disclosureSystemName", help=SUPPRESS_HELP)
        parser.add_option("--disclosureSystem", action="store", dest="disclosureSystemName",
                        help=_("Specify a disclosure system name and"
                                " select disclosure system validation.  "
                                "Enter --disclosureSystem=help for list of names or help-verbose for list of names and descriptions. "))
        parser.add_option("--disclosuresystem", action="store", dest="disclosureSystemName", help=SUPPRESS_HELP)
        parser.add_option("--hmrc", action="store_true", dest="validateHMRC",
                        help=_("Select U.K. HMRC disclosure system validation."))
        parser.add_option("--utr", action="store_true", dest="utrValidate",
                        help=_("Select validation with respect to Unit Type Registry."))
        parser.add_option("--utrUrl", action="store", dest="utrUrl",
                        help=_("Override disclosure systems Unit Type Registry location (URL or file path)."))
        parser.add_option("--utrurl", action="store", dest="utrUrl", help=SUPPRESS_HELP)
        parser.add_option("--infoset", action="store_true", dest="infosetValidate",
                        help=_("Select validation with respect testcase infosets."))
        parser.add_option("--labelLang", action="store", dest="labelLang",
                        help=_("Language for labels in following file options (override system settings)"))
        parser.add_option("--labellang", action="store", dest="labelLang", help=SUPPRESS_HELP)
        parser.add_option("--labelRole", action="store", dest="labelRole",
                        help=_("Label role for labels in following file options (instead of standard label)"))
        parser.add_option("--labelrole", action="store", dest="labelRole", help=SUPPRESS_HELP)
        parser.add_option("--DTS", "--csvDTS", action="store", dest="DTSFile",
                        help=_("Write DTS tree into FILE (may be .csv or .html)"))
        parser.add_option("--facts", "--csvFacts", action="store", dest="factsFile",
                        help=_("Write fact list into FILE"))
        parser.add_option("--factListCols", action="store", dest="factListCols",
                        help=_("Columns for fact list file"))
        parser.add_option("--factTable", "--csvFactTable", action="store", dest="factTableFile",
                        help=_("Write fact table into FILE"))
        parser.add_option("--concepts", "--csvConcepts", action="store", dest="conceptsFile",
                        help=_("Write concepts into FILE"))
        parser.add_option("--pre", "--csvPre", action="store", dest="preFile",
                        help=_("Write presentation linkbase into FILE"))
        parser.add_option("--table", "--csvTable", action="store", dest="tableFile",
                        help=_("Write table linkbase into FILE"))
        parser.add_option("--cal", "--csvCal", action="store", dest="calFile",
                        help=_("Write calculation linkbase into FILE"))
        parser.add_option("--dim", "--csvDim", action="store", dest="dimFile",
                        help=_("Write dimensions (of definition) linkbase into FILE"))
        parser.add_option("--anch", action="store", dest="anchFile",
                        help=_("Write anchoring relationships (of definition) linkbase into FILE"))
        parser.add_option("--formulae", "--htmlFormulae", action="store", dest="formulaeFile",
                        help=_("Write formulae linkbase into FILE"))
        parser.add_option("--viewArcrole", action="store", dest="viewArcrole",
                        help=_("Write linkbase relationships for viewArcrole into viewFile"))
        parser.add_option("--viewarcrole", action="store", dest="viewArcrole", help=SUPPRESS_HELP)
        parser.add_option("--viewFile", action="store", dest="viewFile",
                        help=_("Write linkbase relationships for viewArcrole into viewFile"))
        parser.add_option("--relationshipCols", action="store", dest="relationshipCols",
                        help=_("Extra columns for relationship file (comma or space separated: Name, Namespace, LocalName, Documentation and References)"))
        parser.add_option("--relationshipcols", action="store", dest="relationshipCols", help=SUPPRESS_HELP)
        parser.add_option("--viewfile", action="store", dest="viewFile", help=SUPPRESS_HELP)
        parser.add_option("--roleTypes", action="store", dest="roleTypesFile",
                        help=_("Write defined role types into FILE"))
        parser.add_option("--roletypes", action="store", dest="roleTypesFile", help=SUPPRESS_HELP)
        parser.add_option("--arcroleTypes", action="store", dest="arcroleTypesFile",
                        help=_("Write defined arcrole types into FILE"))
        parser.add_option("--arcroletypes", action="store", dest="arcroleTypesFile", help=SUPPRESS_HELP)
        parser.add_option("--testReport", "--csvTestReport", action="store", dest="testReport",
                        help=_("Write test report of validation (of test cases) into FILE"))
        parser.add_option("--testreport", "--csvtestreport", action="store", dest="testReport", help=SUPPRESS_HELP)
        parser.add_option("--testReportCols", action="store", dest="testReportCols",
                        help=_("Columns for test report file"))
        parser.add_option("--testreportcols", action="store", dest="testReportCols", help=SUPPRESS_HELP)
        parser.add_option("--rssReport", action="store", dest="rssReport",
                        help=_("Write RSS report into FILE"))
        parser.add_option("--rssreport", action="store", dest="rssReport", help=SUPPRESS_HELP)
        parser.add_option("--rssReportCols", action="store", dest="rssReportCols",
                        help=_("Columns for RSS report file"))
        parser.add_option("--rssreportcols", action="store", dest="rssReportCols", help=SUPPRESS_HELP)
        parser.add_option("--skipDTS", action="store_true", dest="skipDTS",
                        help=_("Skip DTS activities (loading, discovery, validation), useful when an instance needs only to be parsed."))
        parser.add_option("--skipdts", action="store_true", dest="skipDTS", help=SUPPRESS_HELP)
        parser.add_option("--skipLoading", action="store", dest="skipLoading",
                        help=_("Skip loading discovered or schemaLocated files matching pattern (unix-style file name patterns separated by '|'), useful when not all linkbases are needed."))
        parser.add_option("--skiploading", action="store", dest="skipLoading", help=SUPPRESS_HELP)
        parser.add_option("--logFile", action="store", dest="logFile",
                        help=_("Write log messages into file, otherwise they go to standard output.  " 
                                "If file ends in .xml it is xml-formatted, otherwise it is text. "))
        parser.add_option("--logfile", action="store", dest="logFile", help=SUPPRESS_HELP)
        parser.add_option("--logFormat", action="store", dest="logFormat",
                        help=_("Logging format for messages capture, otherwise default is \"[%(messageCode)s] %(message)s - %(file)s\"."))
        parser.add_option("--logformat", action="store", dest="logFormat", help=SUPPRESS_HELP)
        parser.add_option("--logLevel", action="store", dest="logLevel",
                        help=_("Minimum level for messages capture, otherwise the message is ignored.  " 
                                "Current order of levels are debug, info, info-semantic, warning, warning-semantic, warning, assertion-satisfied, inconsistency, error-semantic, assertion-not-satisfied, and error. "))
        parser.add_option("--loglevel", action="store", dest="logLevel", help=SUPPRESS_HELP)
        parser.add_option("--logLevelFilter", action="store", dest="logLevelFilter",
                        help=_("Regular expression filter for logLevel.  " 
                                "(E.g., to not match *-semantic levels, logLevelFilter=(?!^.*-semantic$)(.+). "))
        parser.add_option("--loglevelfilter", action="store", dest="logLevelFilter", help=SUPPRESS_HELP)
        parser.add_option("--logCodeFilter", action="store", dest="logCodeFilter",
                        help=_("Regular expression filter for log message code."))
        parser.add_option("--logcodefilter", action="store", dest="logCodeFilter", help=SUPPRESS_HELP)
        parser.add_option("--logTextMaxLength", action="store", dest="logTextMaxLength", type="int",
                        help=_("Log file text field max length override."))
        parser.add_option("--logtextmaxlength", action="store", dest="logTextMaxLength", type="int", help=SUPPRESS_HELP)
        parser.add_option("--logRefObjectProperties", action="store_true", dest="logRefObjectProperties", 
                        help=_("Log reference object properties (default)."), default=True)
        parser.add_option("--logrefobjectproperties", action="store_true", dest="logRefObjectProperties", help=SUPPRESS_HELP)
        parser.add_option("--logNoRefObjectProperties", action="store_false", dest="logRefObjectProperties", 
                        help=_("Do not log reference object properties."))
        parser.add_option("--lognorefobjectproperties", action="store_false", dest="logRefObjectProperties", help=SUPPRESS_HELP)
        parser.add_option("--statusPipe", action="store", dest="statusPipe", help=SUPPRESS_HELP)
        parser.add_option("--monitorParentProcess", action="store", dest="monitorParentProcess", help=SUPPRESS_HELP)
        parser.add_option("--outputAttribution", action="store", dest="outputAttribution", help=SUPPRESS_HELP)
        parser.add_option("--outputattribution", action="store", dest="outputAttribution", help=SUPPRESS_HELP)
        parser.add_option("--showOptions", action="store_true", dest="showOptions", help=SUPPRESS_HELP)
        parser.add_option("--parameters", action="store", dest="parameters", help=_("Specify parameters for formula and validation (name=value[,name=value])."))
        parser.add_option("--parameterSeparator", action="store", dest="parameterSeparator", help=_("Specify parameters separator string (if other than comma)."))
        parser.add_option("--parameterseparator", action="store", dest="parameterSeparator", help=SUPPRESS_HELP)
        parser.add_option("--formula", choices=("validate", "run", "none"), dest="formulaAction", 
                        help=_("Specify formula action: "
                                "validate - validate only, without running, "
                                "run - validate and run, or "
                                "none - prevent formula validation or running when also specifying -v or --validate.  "
                                "if this option is not specified, -v or --validate will validate and run formulas if present"))
        parser.add_option("--formulaParamExprResult", action="store_true", dest="formulaParamExprResult", help=_("Specify formula tracing."))
        parser.add_option("--formulaparamexprresult", action="store_true", dest="formulaParamExprResult", help=SUPPRESS_HELP)
        parser.add_option("--formulaParamInputValue", action="store_true", dest="formulaParamInputValue", help=_("Specify formula tracing."))
        parser.add_option("--formulaparaminputvalue", action="store_true", dest="formulaParamInputValue", help=SUPPRESS_HELP)
        parser.add_option("--formulaCallExprSource", action="store_true", dest="formulaCallExprSource", help=_("Specify formula tracing."))
        parser.add_option("--formulacallexprsource", action="store_true", dest="formulaCallExprSource", help=SUPPRESS_HELP)
        parser.add_option("--formulaCallExprCode", action="store_true", dest="formulaCallExprCode", help=_("Specify formula tracing."))
        parser.add_option("--formulacallexprcode", action="store_true", dest="formulaCallExprCode", help=SUPPRESS_HELP)
        parser.add_option("--formulaCallExprEval", action="store_true", dest="formulaCallExprEval", help=_("Specify formula tracing."))
        parser.add_option("--formulacallexpreval", action="store_true", dest="formulaCallExprEval", help=SUPPRESS_HELP)
        parser.add_option("--formulaCallExprResult", action="store_true", dest="formulaCallExprResult", help=_("Specify formula tracing."))
        parser.add_option("--formulacallexprtesult", action="store_true", dest="formulaCallExprResult", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarSetExprEval", action="store_true", dest="formulaVarSetExprEval", help=_("Specify formula tracing."))
        parser.add_option("--formulavarsetexpreval", action="store_true", dest="formulaVarSetExprEval", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarSetExprResult", action="store_true", dest="formulaVarSetExprResult", help=_("Specify formula tracing."))
        parser.add_option("--formulavarsetexprresult", action="store_true", dest="formulaVarSetExprResult", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarSetTiming", action="store_true", dest="timeVariableSetEvaluation", help=_("Specify showing times of variable set evaluation."))
        parser.add_option("--formulavarsettiming", action="store_true", dest="timeVariableSetEvaluation", help=SUPPRESS_HELP)
        parser.add_option("--formulaAsserResultCounts", action="store_true", dest="formulaAsserResultCounts", help=_("Specify formula tracing."))
        parser.add_option("--formulaasserresultcounts", action="store_true", dest="formulaAsserResultCounts", help=SUPPRESS_HELP)
        parser.add_option("--formulaSatisfiedAsser", action="store_true", dest="formulaSatisfiedAsser", help=_("Specify formula tracing."))
        parser.add_option("--formulasatisfiedasser", action="store_true", dest="formulaSatisfiedAsser", help=SUPPRESS_HELP)
        parser.add_option("--formulaUnsatisfiedAsser", action="store_true", dest="formulaUnsatisfiedAsser", help=_("Specify formula tracing."))
        parser.add_option("--formulaunsatisfiedasser", action="store_true", dest="formulaUnsatisfiedAsser", help=SUPPRESS_HELP)
        parser.add_option("--formulaUnsatisfiedAsserError", action="store_true", dest="formulaUnsatisfiedAsserError", help=_("Specify formula tracing."))
        parser.add_option("--formulaunsatisfiedassererror", action="store_true", dest="formulaUnsatisfiedAsserError", help=SUPPRESS_HELP)
        parser.add_option("--formulaUnmessagedUnsatisfiedAsser", action="store_true", dest="formulaUnmessagedUnsatisfiedAsser", help=_("Specify trace messages for unsatisfied assertions with no formula messages."))
        parser.add_option("--formulaunmessagedunsatisfiedasser", action="store_true", dest="formulaUnmessagedUnsatisfiedAsser", help=SUPPRESS_HELP)
        parser.add_option("--formulaFormulaRules", action="store_true", dest="formulaFormulaRules", help=_("Specify formula tracing."))
        parser.add_option("--formulaformularules", action="store_true", dest="formulaFormulaRules", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarsOrder", action="store_true", dest="formulaVarsOrder", help=_("Specify formula tracing."))
        parser.add_option("--formulavarsorder", action="store_true", dest="formulaVarsOrder", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarExpressionSource", action="store_true", dest="formulaVarExpressionSource", help=_("Specify formula tracing."))
        parser.add_option("--formulavarexpressionsource", action="store_true", dest="formulaVarExpressionSource", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarExpressionCode", action="store_true", dest="formulaVarExpressionCode", help=_("Specify formula tracing."))
        parser.add_option("--formulavarexpressioncode", action="store_true", dest="formulaVarExpressionCode", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarExpressionEvaluation", action="store_true", dest="formulaVarExpressionEvaluation", help=_("Specify formula tracing."))
        parser.add_option("--formulavarexpressionevaluation", action="store_true", dest="formulaVarExpressionEvaluation", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarExpressionResult", action="store_true", dest="formulaVarExpressionResult", help=_("Specify formula tracing."))
        parser.add_option("--formulavarexpressionresult", action="store_true", dest="formulaVarExpressionResult", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarFilterWinnowing", action="store_true", dest="formulaVarFilterWinnowing", help=_("Specify formula tracing."))
        parser.add_option("--formulavarfilterwinnowing", action="store_true", dest="formulaVarFilterWinnowing", help=SUPPRESS_HELP)
        parser.add_option("--formulaVarFiltersResult", action="store_true", dest="formulaVarFiltersResult", help=_("Specify formula tracing."))
        parser.add_option("--formulavarfiltersresult", action="store_true", dest="formulaVarFiltersResult", help=SUPPRESS_HELP)
        parser.add_option("--testcaseResultsCaptureWarnings", action="store_true", dest="testcaseResultsCaptureWarnings",
                        help=_("For testcase variations capture warning results, default is inconsistency or warning if there is any warning expected result.  "))
        parser.add_option("--testcaseresultscapturewarnings", action="store_true", dest="testcaseResultsCaptureWarnings", help=SUPPRESS_HELP)
        parser.add_option("--testcaseResultOptions", choices=("match-any", "match-all"), action="store", dest="testcaseResultOptions",
                        help=_("For testcase results, default is match any expected result, options to match any or match all expected result(s).  "))
        parser.add_option("--formulaRunIDs", action="store", dest="formulaRunIDs", help=_("Specify formula/assertion IDs to run, separated by a '|' character."))
        parser.add_option("--formularunids", action="store", dest="formulaRunIDs", help=SUPPRESS_HELP)
        parser.add_option("--formulaCompileOnly", action="store_true", dest="formulaCompileOnly", help=_("Specify formula are to be compiled but not executed."))
        parser.add_option("--formulacompileonly", action="store_true", dest="formulaCompileOnly", help=SUPPRESS_HELP)
        parser.add_option("--uiLang", action="store", dest="uiLang",
                        help=_("Language for user interface (override system settings, such as program messages).  Does not save setting."))
        parser.add_option("--uilang", action="store", dest="uiLang", help=SUPPRESS_HELP)
        parser.add_option("--proxy", action="store", dest="proxy",
                        help=_("Modify and re-save proxy settings configuration.  " 
                                "Enter 'system' to use system proxy setting, 'none' to use no proxy, "
                                "'http://[user[:password]@]host[:port]' "
                                " (e.g., http://192.168.1.253, http://example.com:8080, http://joe:secret@example.com:8080), "
                                " or 'show' to show current setting, ." ))
        parser.add_option("--internetConnectivity", choices=("online", "offline"), dest="internetConnectivity", 
                        help=_("Specify internet connectivity: online or offline"))
        parser.add_option("--internetconnectivity", action="store", dest="internetConnectivity", help=SUPPRESS_HELP)
        parser.add_option("--internetTimeout", type="int", dest="internetTimeout", 
                        help=_("Specify internet connection timeout in seconds (0 means unlimited)."))
        parser.add_option("--internettimeout", type="int", action="store", dest="internetTimeout", help=SUPPRESS_HELP)
        parser.add_option("--internetRecheck", choices=("weekly", "daily", "never"), action="store", dest="internetRecheck", 
                        help=_("Specify rechecking cache files (weekly is default)"))
        parser.add_option("--internetrecheck", choices=("weekly", "daily", "never"), action="store", dest="internetRecheck", help=SUPPRESS_HELP)
        parser.add_option("--internetLogDownloads", action="store_true", dest="internetLogDownloads", 
                        help=_("Log info message for downloads to web cache."))
        parser.add_option("--internetlogdownloads", action="store_true", dest="internetLogDownloads", help=SUPPRESS_HELP)
        parser.add_option("--noCertificateCheck", action="store_true", dest="noCertificateCheck", 
                        help=_("Specify no checking of internet secure connection certificate"))
        parser.add_option("--nocertificatecheck", action="store_true", dest="noCertificateCheck", help=SUPPRESS_HELP)
        parser.add_option("--xdgConfigHome", action="store", dest="xdgConfigHome", 
                        help=_("Specify non-standard location for configuration and cache files (overrides environment parameter XDG_CONFIG_HOME)."))
        parser.add_option("--plugins", action="store", dest="plugins",
                        help=_("Specify plug-in configuration for this invocation.  "
                                "Enter 'show' to confirm plug-in configuration.  "
                                "Commands show, and module urls are '|' separated: "
                                "url specifies a plug-in by its url or filename, "
                                "relative URLs are relative to installation plug-in directory, "
                                " (e.g., 'http://arelle.org/files/hello_web.py', 'C:\Program Files\Arelle\examples\plugin\hello_dolly.py' to load, "
                                "or ../examples/plugin/hello_dolly.py for relative use of examples directory) "
                                "Local python files do not require .py suffix, e.g., hello_dolly without .py is sufficient, "
                                "Packaged plug-in urls are their directory's url (e.g., --plugins EdgarRenderer or --plugins xbrlDB).  " ))
        parser.add_option("--packages", action="store", dest="packages",
                        help=_("Specify taxonomy packages configuration.  "
                                "Enter 'show' to show current packages configuration.  "
                                "Commands show, and module urls are '|' separated: "
                                "url specifies a package by its url or filename, please use full paths. "
                                "(Package settings from GUI are no longer shared with cmd line operation. "
                                "Cmd line package settings are not persistent.)  " ))
        parser.add_option("--package", action="store", dest="packages", help=SUPPRESS_HELP)
        parser.add_option("--packageManifestName", action="store", dest="packageManifestName",
                        help=_("Provide non-standard archive manifest file name pattern (e.g., *taxonomyPackage.xml).  "
                                "Uses unix file name pattern matching.  "
                                "Multiple manifest files are supported in archive (such as oasis catalogs).  "
                                "(Replaces search for either .taxonomyPackage.xml or catalog.xml).  " ))
        parser.add_option("--abortOnMajorError", action="store_true", dest="abortOnMajorError", help=_("Abort process on major error, such as when load is unable to find an entry or discovered file."))
        parser.add_option("--showEnvironment", action="store_true", dest="showEnvironment", help=_("Show Arelle's config and cache directory and host OS environment parameters."))
        parser.add_option("--showenvironment", action="store_true", dest="showEnvironment", help=SUPPRESS_HELP)
        parser.add_option("--collectProfileStats", action="store_true", dest="collectProfileStats", help=_("Collect profile statistics, such as timing of validation activities and formulae."))
        if hasWebServer:
            parser.add_option("--webserver", action="store", dest="webserver",
                            help=_("start web server on host:port[:server] for REST and web access, e.g., --webserver locahost:8080, "
                                    "or specify nondefault a server name, such as cherrypy, --webserver locahost:8080:cherrypy. "
                                    "(It is possible to specify options to be defaults for the web server, such as disclosureSystem and validations, but not including file names.) "))
        pluginOptionsIndex = len(parser.option_list)

        # MODIFIED:
        # install any dynamic plugins so their command line options can be parsed if present
        # for i, arg in enumerate(args):
        #     if arg.startswith('--plugin'): # allow singular or plural (option must simply be non-ambiguous
        #         if len(arg) > 9 and arg[9] == '=':
        #             preloadPlugins = arg[10:]
        #         elif i < len(args) - 1:
        #             preloadPlugins = args[i+1]

        # Needs to be figured out, initially get plugins so plugin options are available
        # issue is that this might get saved later in do I want to save it? maybe get the
        # plugin code from .run() and add it here and ignore plugin option in .run()?
        if preloadPlugins == None:
            preloadPlugins = ""

        for pluginCmd in preloadPlugins.split('|'):
            cmd = pluginCmd.strip()
            if cmd not in ("show", "temp") and len(cmd) > 0 and cmd[0] not in ('-', '~', '+'):
                moduleInfo = PluginManager.addPluginModule(cmd)
                if moduleInfo:
                    cntlr.preloadedPlugins[cmd] = moduleInfo
                    PluginManager.reset()
        # break

        # add plug-in options
        pluginRef = []
        ref = None
        for optionsExtender in pluginClassMethods("CntlrCmdLine.Options"):
            ref = (optionsExtender.__globals__['__name__'], len(parser.option_list))
            optionsExtender(parser)
            ref = ref + (len(parser.option_list),)
            pluginRef.append(ref)
            
        pluginLastOptionIndex = len(parser.option_list)

        parser.add_option("-a", "--about",
                        action="store_true", dest="about",
                        help=_("Show product version, copyright, and license."))

        return (parser, pluginRef, pluginOptionsIndex, pluginLastOptionIndex)
    

    def parseOpts(self, isDict=True, argsDict=None, **kwargs):
        cntlr = self.cntlr
        hasWebServer = self.hasWebServer
        parser = self.parser
        pluginOptionsIndex = self.pluginOptionsIndex
        pluginLastOptionIndex = self.pluginLastOptionIndex
        args =[]
        if isDict:
            if argsDict:
                for k, v in argsDict.items():
                    args.append(k)
                    if v:
                        args.append(v)
        elif kwargs:
            for k, v in kwargs.items():
                _kw = "--" + k.replace('_', '-')
                args.append(_kw)
                if v:
                    args.append(v)            

        # print(args)

        if not args and cntlr.isGAE:
            args = ["--webserver=::gae"]
        elif cntlr.isCGI:
            args = ["--webserver=::cgi"]
        elif cntlr.isMSW:
            # if called from java on Windows any empty-string arguments are lost, see:
            # http://bugs.java.com/view_bug.do?bug_id=6518827
            # insert needed arguments
            sourceArgs = args
            args = []
            namedOptions = set()
            optionsWithArg = set()
            for option in parser.option_list:
                names = str(option).split('/')
                namedOptions.update(names)
                if option.action == "store":
                    optionsWithArg.update(names)
            priorArg = None
            for arg in sourceArgs:
                if priorArg in optionsWithArg and arg in namedOptions:
                    # probable java/MSFT interface bug 6518827
                    args.append('')  # add empty string argument
                # remove quoting if arguments quoted according to http://bugs.java.com/view_bug.do?bug_id=6518827
                if r'\"' in arg:  # e.g., [{\"foo\":\"bar\"}] -> [{"foo":"bar"}]
                    arg = arg.replace(r'\"', '"')
                args.append(arg)
                priorArg = arg

        # Deal with exits
        if '-help' in args:
            parser.print_help()
            return
        elif '-version' in args:
            parser.print_version()
            return

        (options, leftoverArgs) = parser.parse_args(args)


        if options.about:
            print(_("\narelle(r) {0} ({1}bit)\n\n"
                    "An open source XBRL platform\n"
                    "(c) 2010-{2} Mark V Systems Limited\n"
                    "All rights reserved\nhttp://www.arelle.org\nsupport@arelle.org\n\n"
                    "Licensed under the Apache License, Version 2.0 (the \"License\"); "
                    "you may not \nuse this file except in compliance with the License.  "
                    "You may obtain a copy \nof the License at "
                    "'http://www.apache.org/licenses/LICENSE-2.0'\n\n"
                    "Unless required by applicable law or agreed to in writing, software \n"
                    "distributed under the License is distributed on an \"AS IS\" BASIS, \n"
                    "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  \n"
                    "See the License for the specific language governing permissions and \n"
                    "limitations under the License."
                    "\n\nIncludes:"
                    "\n   Python(r) {4[0]}.{4[1]}.{4[2]} (c) 2001-2013 Python Software Foundation"
                    "\n   PyParsing (c) 2003-2013 Paul T. McGuire"
                    "\n   lxml {5[0]}.{5[1]}.{5[2]} (c) 2004 Infrae, ElementTree (c) 1999-2004 by Fredrik Lundh"
                    "{3}"
                    "\n   May include installable plug-in modules with author-specific license terms"
                    ).format(Version.__version__, cntlr.systemWordSize, Version.copyrightLatestYear,
                            _("\n   Bottle (c) 2011-2013 Marcel Hellkamp") if hasWebServer else "",
                            sys.version_info, etree.LXML_VERSION))
        elif options.disclosureSystemName in ("help", "help-verbose"):
            text = _("Disclosure system choices: \n{0}").format(' \n'.join(cntlr.modelManager.disclosureSystem.dirlist(options.disclosureSystemName)))
            try:
                print(text)
            except UnicodeEncodeError:
                print(text.encode("ascii", "replace").decode("ascii"))
        elif len(leftoverArgs) != 0 and (not hasWebServer or options.webserver is None):
            parser.error(_("unrecognized arguments: {}").format(', '.join(leftoverArgs)))
        elif (options.entrypointFile is None and 
            ((not options.proxy) and (not options.plugins) and
            (not any(pluginOption for pluginOption in parser.option_list[pluginOptionsIndex:pluginLastOptionIndex])) and
            (not hasWebServer or options.webserver is None))):
            parser.error(_("incorrect arguments, please try\n  python CntlrCmdLine.py --help"))
        elif hasWebServer and options.webserver:
            # webserver incompatible with file operations
            if any((options.entrypointFile, options.importFiles, options.diffFile, options.versReportFile,
                    options.factsFile, options.factListCols, options.factTableFile,
                    options.conceptsFile, options.preFile, options.tableFile, options.calFile, options.dimFile, options.formulaeFile, options.viewArcrole, options.viewFile,
                    options.roleTypesFile, options.arcroleTypesFile
                    )):
                parser.error(_("incorrect arguments with --webserver, please try\n  python CntlrCmdLine.py --help"))
            else:
                # note that web server logging does not strip time stamp, use logFormat if that is desired
                cntlr.startLogging(logFileName='logToBuffer',
                                logTextMaxLength=options.logTextMaxLength,
                                logRefObjectProperties=options.logRefObjectProperties)
                # from arelle import CntlrWebMain
                # app = CntlrWebMain.startWebserver(cntlr, options)
                # if options.webserver == '::wsgi':
                #     return app
        else:
            # parse and run the FILENAME
            cntlr.startLogging(logFileName=(options.logFile or "logToPrint"),
                            logFormat=(options.logFormat or "[%(messageCode)s] %(message)s - %(file)s"),
                            logLevel=(options.logLevel or "DEBUG"),
                            logToBuffer=getattr(options, "logToBuffer", False),
                            logTextMaxLength=options.logTextMaxLength, # e.g., used by EdgarRenderer to require buffered logging
                            logRefObjectProperties=options.logRefObjectProperties)
        
        # prevents duplicating log print on re-runs
        _logger = logging.getLogger('arelle')
        for x in _logger.handlers:
            if type(x).__name__ == 'LogToPrintHandler' and not x is cntlr.logHandler:
                _logger.removeHandler(x)
            # cntlr.run(options)
        cntlr.parsedOpts = options    
        return options
