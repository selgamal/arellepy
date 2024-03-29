'''Use arelle from python script
This plugin provides class CntlrPy, that can be used from python code, it mimics exactly
using CntlrCmdLine.

Eventhough there is a python API documented on arelle.org using the Cntlr class, but it is
sometimes difficult to get the same exact results achieved by using CntlrCmdLine. This plugin
and CntlrPy just makes it easier to use the same options from CntlrCmdLine but within python
code or interactive environment, it translates the run options and pass them through to
CntlrCmdLine and keeps it open for further processing and inspection as needed.

This plugin provides a local viewer that can view multiple Edgar reports rendered by the 
EdgarRenderer plugin in the same viewer as a convenience. The only caveat is that the reports
must be rendered from this plugin, the renedering is done normally via EdgarRenderer, but a 
metadata file is added to make the viewer work.

This plugin provides another convenience in running formulae and capturing the results. Formulae
can be stored in a database generated by rssDB plugin and can be run on the search results from
the same database, results can either be stored in the database or in file.
'''
import os, sys, pathlib, gettext, logging, atexit, time
from math import isnan
from collections import defaultdict
from .HelperFuncs import selectRunEnv, arellepyConfig

gettext.install('arelle')
parentDir = list(pathlib.Path(__file__).parents)[0]
pathToLocals = str(os.path.join(parentDir, 'locals'))

memory_used_global = 0
time_start_global = time.time()

cxFrozen = getattr(sys, 'frozen', False)
if not cxFrozen: # do nothing if frozen, it will take care of everything
    conf = arellepyConfig(parentDir)
    os.environ["XDG_ARELLE_RESOURCES_DIR"] = selectRunEnv(**conf)

def arellepyToolBarExtender(cntlr, toolbar):
    try:
        from .LocalViewerStandalone import toolBarExtender
    except:
        from LocalViewerStandalone import toolBarExtender

    toolBarExtender(cntlr, toolbar)

class DuplicateFacts:
    def __init__(self, modelXbrl, cntlr) -> None:
        self.dupFactsIndexes = set()
        self.dup_facts_sets_by_hash = dict()
        self.dup_facts_sets_by_key = dict() # (dup_set_hash, is_inconsistent_dup_set, most_precise_fact)
        self.most_precise_dup_facts_set = set()

        self._getDups(modelXbrl, cntlr)

        self.dupFactsIndexes = {f.objectIndex for f_set in self.dup_facts_sets_by_hash.values() for f in f_set if not f in self.most_precise_dup_facts_set} # does not include most precise
        self.all_dup_facts_indexes = {f.objectIndex for f_set in self.dup_facts_sets_by_hash.values() for f in f_set}
        self.all_dup_facts_sets_indexes = [{f.objectIndex for f in f_set} for f_set in self.dup_facts_sets_by_hash.values()]
        self.consistent_dup_facts_sets_indexes = [{f.objectIndex for f in f_set} for k, f_set in self.dup_facts_sets_by_key.items() if not k[1]]
        self.inconsistent_dup_facts_sets_indexes = [{f.objectIndex for f in f_set} for k, f_set in self.dup_facts_sets_by_key.items() if k[1]]
        self.most_precise_dup_facts_set_indexes = {x.objectIndex for x in self.most_precise_dup_facts_set}

        self.all_dup_facts_sets_count = len(self.dup_facts_sets_by_hash) \
                                                if not self.dup_facts_sets_by_hash is None else 0

        self.all_dup_facts_count = len(self.all_dup_facts_indexes) \
                                                if not self.all_dup_facts_indexes is None else 0

        self.inconsistent_dup_facts_sets_count = len(self.inconsistent_dup_facts_sets_indexes) \
                                                if not self.inconsistent_dup_facts_sets_indexes is None else 0

        self.inconsistent_dup_facts_count = sum([len(x) for x in self.inconsistent_dup_facts_sets_indexes]) \
                                                if not self.inconsistent_dup_facts_sets_indexes is None else 0

        self.consistent_dup_facts_sets_count = len(self.consistent_dup_facts_sets_indexes) \
                                                if not self.consistent_dup_facts_sets_indexes is None else 0

        self.consistent_dup_facts_count = sum([len(x) for x in self.consistent_dup_facts_sets_indexes]) \
                                                if not self.consistent_dup_facts_sets_indexes is None else 0

        stats_msg = _(f'Found {self.all_dup_facts_sets_count} '
                                    f'duplicate facts set(s) (including {self.all_dup_facts_count} fact(s)), '
                                    f'with {self.inconsistent_dup_facts_count} '
                                    f'inconsistent duplicate set(s) (including {self.inconsistent_dup_facts_count} facts)')
        # mx.modelManager.showStatus(stats_msg)
        modelXbrl.dupFactsIndexes = self.dupFactsIndexes
        if modelXbrl is not None and len(getattr(modelXbrl, 'factsInInstance', [])) > 0:
            cntlr.addToLog(stats_msg, file=modelXbrl.uri, messageCode="info", level=logging.INFO)

    def _getDups(self, mx, cntlr):
        '''Detect duplicate facts ids in inline filings, duplicates facts are facts with lesser precision'''
        from arelle.ModelValue import qname
        from arelle.ValidateXbrlCalcs import inferredPrecision
        from arelle.XmlValidate import validate as xValidator
        from arelle.ModelInstanceObject import ModelInlineFact
        factForConceptContextUnitHash = defaultdict(list)
        most_precise_facts_set = set()
        dup_facts_sets_by_hash = {}
        dup_facts_sets_by_key = {} # (dup_set_hash, is_inconsistent_dup_set, most_precise_fact)

        # detect duplicates if we have facts.
        if not len(getattr(mx, 'factsInInstance', [])) > 0:
            return

        l1 =  mx.factsInInstance
        for _f in l1:
            # if _f.xValid == 0:
            #     cntlr.showStatus(f'Invalid before dups check: {_f}')
            factForConceptContextUnitHash[_f.conceptContextUnitHash].append(_f)

        for dup_set_hash, dups in factForConceptContextUnitHash.items():
            if len(dups)>1:
                x_valid_state = {fct:fct.xValid for fct in dups}
                if all([d_f.isNumeric for d_f in dups]):
                    dups.sort(key=lambda x: inferredPrecision(x), reverse=True)
                else:
                    dups.sort(key=lambda x: x.objectIndex, reverse=False)
                most_precise_facts_set.add(dups[0])
                is_inconsistent_dup_set = self._has_inconsistent_duplicates(dups)
                dups_set = {x for x in dups}
                dup_facts_sets_by_hash[dup_set_hash] = dups_set
                dup_facts_sets_by_key[(dup_set_hash, is_inconsistent_dup_set, dups[0])] = dups_set
                for fct in dups:
                    if fct.xValid != x_valid_state[fct]:
                        xValidator(mx, fct, ixFacts=isinstance(fct, ModelInlineFact))

        self.dup_facts_sets_by_hash = dup_facts_sets_by_hash
        self.dup_facts_sets_by_key = dup_facts_sets_by_key
        self.most_precise_dup_facts_set = most_precise_facts_set

    @staticmethod
    def _has_inconsistent_duplicates(fact_dup_list):
        from arelle.ValidateXbrlCalcs import rangeValue, inferredDecimals
        _inConsistent = False
        fList = fact_dup_list
        f0 = fList[0]   
        if f0.concept.isNumeric:
            decVals = {}
            if any(f.isNil for f in fList):
                _inConsistent = not all(f.isNil for f in fList)
            else: # not all have same decimals
                _d = inferredDecimals(f0)
                _v = f0.xValue
                _inConsistent = isnan(_v) # NaN is incomparable, always makes dups inconsistent
                decVals[_d] = _v
                aMax, bMin = rangeValue(_v, _d)
                for f in fList[1:]:
                    _d = inferredDecimals(f)
                    _v = f.xValue
                    if isnan(_v):
                        _inConsistent = True
                        break
                    if _d in decVals:
                        _inConsistent |= _v != decVals[_d]
                    else:
                        decVals[_d] = _v
                    a, b = rangeValue(_v, _d)
                    if a > aMax: aMax = a
                    if b < bMin: bMin = b
                if not _inConsistent:
                    _inConsistent = (bMin < aMax)
        else:
            _inConsistent = any(not f.isVEqualTo(f0) for f in fList[1:])
        return _inConsistent

def arellepyCmdLineOptionExtender(parser, *args, **kwargs):
    parser.add_option("--arellepyRunFormulaFromDB", action='store_true', dest="arellepyRunFormulaFromDB", default=False, 
                        help=_("Flag to initiate runing a formula on search results obtained from rssDB, must have search results and a valid formulaId to run"))

    # parser.add_option("--arellepyRunFormulaFromDBFormulaId", action='store', dest="arellepyRunFormulaFromDBFormulaId", 
    #                     help=_("A formulaId existing in rssDB, must have search results to run"))
    
    parser.add_option("--arellepyRunFormulaFromDBInsertResultIntoDb", action='store_true', dest="arellepyRunFormulaFromDBInsertResultIntoDb", default=False, 
                        help=_("Flag to insert formula output into DB (also updates results existing in db for same formula ran on same filing"
                                 "if updateExistingResults flag is set) This flag is valid only if a value for arellepyRunFormulaId is entered."))
    
    parser.add_option("--arellepyRunFormulaFromDBUpdateExistingResults", action='store_true', dest="arellepyRunFormulaFromDBUpdateExistingResults", default=False, 
                        help=_("Flag to run formula on filings even if those filings having results for the same formula existing in DB, results may be inserted into db if "
                                "arellepyRunFormulaFromDBInsertResultIntoDb flag is set or written to file if arellepyRunFormulaFromDBSaveResultsToFolder flag is set"
                                 "This flag is valid only if arellepyRunFormulaId is set."))
    
    parser.add_option("--arellepyRunFormula", action='store_true', dest="arellepyRunFormula", default=False, 
                        help=_("Flag to run formula from sources other than db, formula can be either valid xml formula linkbase string specified by arellepyRunFormulaFormulaString "
                                "or a path to file specified by arellepyRunFormulaFormulaSourceFile, "
                                " instances to apply formula to are specified by arellepyRunFormulaInstancesUrls, that can be pipe '|' separated instances urls, or "
                                "the term 'FROM_SEARCH' to use search results produced by --rssDBsearch"))  

    parser.add_option("--arellepyRunFormulaInstancesUrls", action='store', dest="arellepyRunFormulaInstancesUrls",
                        help=_("Pipe separated instances urls '|' to apply formula to or the term 'FROM_SEARCH' to use search results produced by --rssDBsearch."
                                "This options is only valid if flag arellepyRunFormula flag is set"))    

    parser.add_option("--arellepyRunFormulaString", action='store', dest="arellepyRunFormulaString",
                        help=_("String for valid formula linkbase to apply to instances specified by arellepyRunFormulaInstancesUrls, only valid if flag arellepyRunFormula flag is set"))    

    parser.add_option("--arellepyRunFormulaSourceFile", action='store', dest="arellepyRunFormulaSourceFile",
                        help=_("Path to formula linkbase file to apply to instances specified by arellepyRunFormulaInstancesUrls, only valid if arellepyRunFormula flag is set, " 
                                "if arellepyRunFormulaString is also specified, this file will be ignored and the string is used"))    

    parser.add_option("--arellepyRunFormulaId", action='store', dest="arellepyRunFormulaId",
                        help=_("If arellepyRunFormulaFromDB flag is set this must be a formulaId existing in rssDB, and is applied on rssDB search result, if arellepyRunFormula flag is set this is used only for file name to store output"))    

    parser.add_option("--arellepyRunFormulaWriteFormulaToSourceFile", action='store', dest="arellepyRunFormulaWriteFormulaToSourceFile",
                        help=_("Writes string from arellepyRunFormulaString to arellepyRunformulaSourceFile, only valid if arellepyRunFormula flag is set."))    
    

    parser.add_option("--arellepyRunFormulaSaveResultsToFolder", action='store_true', dest="arellepyRunFormulaSaveResultsToFolder", default=False, 
                        help=_("Flag to write formula results to files in folder specified by arellepyRunFormulaFolderPath, "
                                "file name is a combination of formula id, filing id (or instance file name) and date"))
    
    parser.add_option("--arellepyRunFormulaFolderPath", action='store', dest="arellepyRunFormulaFolderPath", default=None, 
                        help=_("Path to folder to write formula results files, only valid if arellepyRunFormulaSaveResultsToFolder"))
    

def utilityRun(cntlr, options, **kwargs):
    # print('arellepy utility run now!!')
    if options.arellepyRunFormula:
        if options.arellepyRunFormulaFromDB:
            cntlr.addToLog(_('Only one of  "--arellepyRunFormulaFromDB" or "--arellepyRunFormula" can be chosen'),
                    messageCode="arellepy.Error",  file=__name__,  level=logging.ERROR)
            raise Exception(_('Only one of  "--arellepyRunFormulaFromDB" or "--arellepyRunFormula" can be chosen'))


def xbrlLoaded(cntlr, options, modelXbrl, *args, **kwargs):
    # modelXbrl.duplicateFactsInfo = DuplicateFacts(modelXbrl, cntlr)
    pass

def filingEnd(cntlr, options, filesource, _entrypointFiles, *args, **kwargs):
    global memory_used_global, time_start_global
    modelXbrl = cntlr.modelManager.modelXbrl
    startedAt = time.time()
    modelXbrl.duplicateFactsInfo = DuplicateFacts(modelXbrl, cntlr)
    modelXbrl.profileStat(("arellepy: detect-duplicates"), time.time() - startedAt)
    modelXbrl.memory_change = cntlr.memoryUsed - memory_used_global
    modelXbrl.load_end_time = time.time()
    modelXbrl.load_start_time = time_start_global
    modelXbrl.time_to_load = modelXbrl.load_end_time - modelXbrl.load_start_time # profile stat capture load time also, this provides useful datetime for start/end

def filingStart(cntlr, options, *args, **kwargs):
    global memory_used_global, time_start_global
    memory_used_global = cntlr.memoryUsed
    time_start_global = time.time()


def initFunc(cntlr, **kwargs):
    # print('arellepy init run now!!')
    # Add temps folder to config dir
    if not hasattr(cntlr, 'userAppTempDir'):
        cntlr.userAppTempDir = os.path.join(cntlr.userAppDir, 'temps')
        if not os.path.exists(cntlr.userAppTempDir):
            os.mkdir(cntlr.userAppTempDir)
    
    # clean up temp files on exit
    def cleanTemps(dir):
        #clean up
        for f in os.listdir(dir):
            f_path = os.path.join(dir, f)
            os.remove(f_path)
    if not getattr(cntlr, 'atExitAdded', False):
        atexit.register(cleanTemps, cntlr.userAppTempDir)
        cntlr.atExitAdded = True


__pluginInfo__ = {
    'name': 'arellepy',
    'version': '0.01',
    'description': "cntrl class for interactive environment (treat Arelle installation or source code as python package).  ",
    'license': 'Apache-2 (Arelle plug-in), BSD license (pg8000 library)',
    'author': 'Sherif ElGamal',
    'CntlrCmdLine.Options': arellepyCmdLineOptionExtender,
    'CntlrCmdLine.Utility.Run': utilityRun,
    'CntlrCmdLine.Xbrl.Loaded': xbrlLoaded,
    'CntlrCmdLine.Filing.Start': filingStart,
    'CntlrCmdLine.Filing.End': filingEnd,
    'CntlrWinMain.Toolbar': arellepyToolBarExtender,
    'Cntlr.Init': initFunc

}
