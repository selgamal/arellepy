'''Use arelle from python script

This plugin provides class CntlrPy, that can be used from python code, it mimics exactly
using CntlrCmdLine.

Eventhough there is a python API documented on arelle.org using the Cntlr class, but it is
sometimes difficult to get the same exact results achieved by using CntlrCmdLine. This plugin
and CntlrPy just makes it easier to use the same options from CntlrCmdLine but withing python
code or even interactive environment, it translates the run options and pass them through to
CntlrCmdLine and keeps it open for further processing as needed.

This plugin provides a local viewer that can view multiple Edgar reports rendered by the 
EdgarRenderer plugin in the same viewer, just a convenience. The only caveat is that the reports
must be rendered from this plugin, the renedering is done normally via EdgarRenderer, but a 
metadata file is added to make the viewer work.

This plugin provides another convenience in running formulae and capturing the results. Formulae
can be stored in a database generated by rssDB plugin and can be run on the search results from
the same database, results can either be stored in the database or in file.
'''
import os, sys, pathlib, gettext, logging, atexit, json
from .HelperFuncs import selectRunEnv, arellepyConfig

gettext.install('arelle')
parentDir = list(pathlib.Path(__file__).parents)[0]
pathToLocals = str(os.path.join(parentDir, 'locals'))

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
    print('arellepy utility run now!!')
    if options.arellepyRunFormula:
        if options.arellepyRunFormulaFromDB:
            cntlr.addToLog(_('Only one of  "--arellepyRunFormulaFromDB" or "--arellepyRunFormula" can be chosen'),
                    messageCode="arellepy.Error",  file=__name__,  level=logging.ERROR)
            raise Exception(_('Only one of  "--arellepyRunFormulaFromDB" or "--arellepyRunFormula" can be chosen'))

def getDups(mx, cntlr):
    from arelle.ModelValue import qname
    from arelle.ValidateXbrlCalcs import inferredPrecision
    dupIds = set()
    processedFactsSet = set()
    if not getattr(mx, 'facts', False):
        return
    l1 =  mx.facts
    for f1 in l1:
        if f1.id in dupIds or f1.id in processedFactsSet:
            continue
        else:
            dups = [f2 for f2 in l1 if f2.isDuplicateOf(f1)]
            if len(dups)>0:
                dups.append(f1) # to compare to duplicates and get the most precise
                dups.sort(key=lambda x: inferredPrecision(x), reverse=True)
                most_precise = dups.pop(0)
                processedFactsSet.add(most_precise.id)
                for dupF in dups:
                    dupIds.add(dupF.id)
            else:
                processedFactsSet.add(f1)
    mx.modelManager.showStatus(_(f'Found {len(dupIds)} duplicate Facts'))
    mx.dupFactsIds = dupIds
    cntlr.modelManager.formulaOptions.parameterValues[qname('param_DUPs_IDs')] = (None, dupIds) #(None,'|'.join(dupIds))


def xbrlLoaded(cntlr, options, modelXbrl, *args, **kwargs):
    getDups(mx=modelXbrl)


# dummy function for class 'Cntlr.Init' to force arelle gui to reload
def initFunc(cntlr, **kwargs):
    print('arellepy init run now!!')
    if not hasattr(cntlr, 'userAppTempDir'):
        cntlr.userAppTempDir = os.path.join(cntlr.userAppDir, 'temps')
        if not os.path.exists(cntlr.userAppTempDir):
            os.mkdir(cntlr.userAppTempDir)

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
    'description': "cntrl class to work with interactively.  ",
    'license': 'Apache-2 (Arelle plug-in), BSD license (pg8000 library)',
    'author': 'Sherif ElGamal',
    'CntlrCmdLine.Options': arellepyCmdLineOptionExtender,
    'CntlrCmdLine.Utility.Run': utilityRun,
    'CntlrCmdLine.Xbrl.Loaded': xbrlLoaded,
    'CntlrWinMain.Toolbar': arellepyToolBarExtender,
    'Cntlr.Init': initFunc

}