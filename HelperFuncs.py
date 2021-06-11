""" :mod: `CntlrPy`
Utility helper functions
""" 

import sys, os, zipfile, warnings, re, json, tempfile
from lxml import etree, html
from urllib import request, parse
from datetime import datetime
from collections import OrderedDict
import time



class CntlrPyWarning(Warning):
    """Warning class"""


def cntlrpyWarningFmt(message, category, filename, lineno, fmt: str, line=None):
    """Function to format a warning the standard way."""
    s = fmt.replace('message', message.__str__())\
        .replace('category', category.__name__)\
            .replace('filename', filename)\
                .replace('lineno', str(lineno)) + '\n'
    return s


def cntlrpy_showwarning(message, category, filename, lineno, file=None, line=None):
    """Hook to write a warning to a file; replace if you like."""
    if file is None:
        file = sys.stderr
        if file is None:
            # sys.stderr is None when run with pythonw.exe - warnings get lost
            return
    try:
        if category.__name__ == 'CntlrPyWarning':
            file.write(
                cntlrpyWarningFmt(message, category, filename, lineno, 
                                 'Warning: category - message\n filename:lineno',
                                 line))
        else:
            file.write(warnings.formatwarning(
                message, category, filename, lineno, line))
    except OSError:
        pass  # the file (probably stderr) is invalid - this warning gets lost

# warnings.showwarning = cntlrpy_showwarning

# warnings.filterwarnings("always", category=CntlrPyWarning)

def chkToList(funcInput, originType: type, chkFunc=None, conversionFunc=None, raiseErr=True):
    """chkToList Checks if input is of correct origintype and converts to list

    Purpose is to be able to pass a list or a single value to a function and have it produce
    results accordingly, for example a dir path or list of dir paths for plugins can be passed
    to a function, and the function will process each element of the list as it would process
    a single input. Additionally a function returning a bool may be used to check input as an
    additional check for the list elements, for example a list of strings is required to be
    valid dir paths `chkFunc` can be `os.path.isdir`.

    Arguments:
        funcInput {any atomic type or list thereof} -- input received from the function
        originType {type} -- The type expected by the receiving function

    Keyword Arguments:
        chkFunc {function} -- a function receiving a single value and returning bool that
        perfoms a check on the value received (default: {None})

    Returns:
        list -- always returns a list, single values are processed as one element list.
    """
    def _msg(_input, trgtType):
        msg = (
            'Cannot work with {c} of type {a}, expecting '
            'elements or list of elements convertable to type {b}'
        ).format(c= _input, a=type(_input).__name__, b=trgtType.__name__)
        return msg

    result = funcInput if isinstance(funcInput, list) else [funcInput]

    for i, inpt in enumerate(result):
        if not isinstance(inpt, originType):
            try:
                result[i] = conversionFunc(inpt) if conversionFunc else originType(inpt)
            except Exception as e:
                if raiseErr:
                    raise e
                else:
                    warnings.warn(_msg(inpt,originType))
        if chkFunc:
            _chk = chkFunc(inpt)
            if not isinstance(_chk, bool):
                raise Exception('chkFunc result is not of type bool')                
            if not _chk:
                chkMsg = '{} failed {} check'.format(inpt, chkFunc.__name__)
                if raiseErr:
                    raise Exception(chkMsg)
                else:
                    warnings.warn(chkMsg)
    return result

def makeLocator(lookInPaths, extractInst: bool = False, CreateUpdatelocatorPath: str = None):
    """Discover folders containing EdgarRenderer reports within given paths

    Looks into folders to discover which subfolders contains a valid EdgarRenderer reports and
    returns reference to each folder and basic data to be used by viewer (locators). Can save and
    update information if desired.

    Arguments:
        lookInPaths {list} -- List of paths

    Keyword Arguments:
        extractInst {bool} -- Extract zipped instance if found in report folder to be used by viewer
        (default: {False})
        CreateUpdatelocatorPath {str} -- A path to json file to save locator data to be used later
        OR is no file exists, create file (default: {None})

    Returns:
        dict -- with 2 values; savedLocatorFile path (False if no file is selected),
        'locators' for discovered reports info to be used by viewer.
    """
    folders = []
    if lookInPaths:
        for i in chkToList(lookInPaths, str, os.path.exists):
            for parent, dirs, files in os.walk(i):
                for d in dirs:
                    folders.append(os.path.join(parent, d))

    finalDict = OrderedDict()
    for f in folders:
        filingSummary = os.path.join(f, 'FilingSummary.xml')
        metaInfo = os.path.join(f, 'additionalMeta.json')
        if os.path.isfile(filingSummary) and os.path.isfile(metaInfo):
            tree = etree.parse(filingSummary)
            instanceFile = tree.xpath('.//@instance')[0]
            inst = 'Not discoverable'
            if instanceFile in os.listdir(f):
                inst = os.path.join(f, instanceFile)
            else:
                zipFiles = [os.path.join(f, x)
                            for x in os.listdir(f) if x.endswith('.zip')]
                if zipFiles:
                    for z in zipFiles:
                        with zipfile.ZipFile(z, 'r') as _zf:
                            if instanceFile in _zf.namelist():
                                if extractInst:
                                    inst = _zf.extract(instanceFile, f)
                                else:
                                    inst = os.path.join(f, instanceFile)
                                break
            res_c = dict()
            with open(metaInfo, 'r') as _addInfo:
                res_c=json.load(_addInfo)
                res_c['reportFolder'] = f
            # make unique folders locators keys
            _i = 1
            _k = os.path.basename(f)
            while _k in list(finalDict.keys()):
                _k = os.path.basename(f) + '_{}'.format(_i)
                _i += 1               
            finalDict[_k] = res_c
    if CreateUpdatelocatorPath:
        if os.path.isfile(CreateUpdatelocatorPath):
            try:
                with open(CreateUpdatelocatorPath, 'r') as j:
                    loc = json.load(j, object_pairs_hook=OrderedDict)
            except Exception as e:
                warnings.warn('file {} is not loadable json file, exception {}:\n{}'.format(
                    CreateUpdatelocatorPath, type(e), e), CntlrPyWarning)
                locFile = os.path.join(os.path.dirname(
                    CreateUpdatelocatorPath), 'locator.json')
                reg = re.compile(r'\s\(\d+\)$')
                _i = 1
                while os.path.isfile(locFile):
                    if reg.search(locFile):
                        locFile = re.sub(reg, '', locFile)
                    locFile = ''.join('{} ({})'.format(locFile, _i))
                    _i += 1
                warnings.warn('Creating locator file {}'.format(
                    locFile), CntlrPyWarning)
                with open(locFile, 'w') as l:
                    json.dump(finalDict, l)
                return {'savedLocatorFile': locFile, 'locators': finalDict}

            warnings.warn('Updating existing file {}'.format(
                CreateUpdatelocatorPath), CntlrPyWarning)
            m = 0
            for c in finalDict:
                match = any([finalDict[c]['dataAttrs'] ==
                             loc[l]['dataAttrs'] for l in loc])
                if not match:
                    loc[c] = finalDict[c]
                    print('adding {} to locator at {}'.format(
                        c, CreateUpdatelocatorPath))
                    m += 1
            if m > 0:
                with open(CreateUpdatelocatorPath, 'w') as j:
                    json.dump(loc, j)
            print('Added {} new items to {}'.format(m, CreateUpdatelocatorPath))
            return {'savedLocatorFile': CreateUpdatelocatorPath, 'locators': loc}
        else:
            if os.path.exists(os.path.dirname(CreateUpdatelocatorPath)):
                with open(CreateUpdatelocatorPath, 'x') as new_j:
                    json.dump(finalDict, new_j)
                print('Locator file created at {}'.format(
                    CreateUpdatelocatorPath))
                return {'savedLocatorFile': CreateUpdatelocatorPath, 'locators': finalDict}
            else:
                warnings.warn('Path {} does not exist, locator file was not created'.format(
                    os.path.dirname(CreateUpdatelocatorPath)))
    return {'savedLocatorFile': False, 'locators': finalDict}

def convert_size(sizeInBytes, unit='bytes'):
    '''Returns human readable object size, unit maybe 'KB', 'MB', 'GB', 'bytes' '''
    conversion = {
        'KB': lambda x: x/1024,
        'MB': lambda x: x/(1024*1024),
        'GB': lambda x: x/(1024*1024*1024),
        'bytes': lambda x: x 
    }

    converted = (round(conversion[unit](sizeInBytes),3), unit)
    suggested = ''
    for x in ['GB', 'MB', 'KB', 'bytes']:
        if round(conversion[x](sizeInBytes),2) > 1:
            _suggested = round(conversion[x](sizeInBytes),2)
            suggested = '{:,.2f} {}'.format(_suggested, x)
            break
    
    return  converted + (suggested,)#(round(conversion[unit](sizeInBytes),3), unit)
    
def get_size(start_path = '.', unit='bytes'):
    '''Returns folder size, unit maybe 'KB', 'MB', 'GB', 'bytes' '''
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    conversion = {
        'KB': lambda x: x/1024,
        'MB': lambda x: x/(1024*1024),
        'GB': lambda x: x/(1024*1024*1024),
        'bytes': lambda x: x 
    }

    return (round(conversion[unit](total_size),3), unit)

def arellepyConfig(parentDir):
    config = {'srcDir':None, 'appDir':None, 'env':None}
    configFile = os.path.join(parentDir, 'arellepyConfig.json')
    if os.path.isfile(configFile): # check if we already have configuration
        with open(configFile, 'r') as fd:
            config = json.load(fd)
    else:
        with open(configFile, 'w') as fd:
            json.dump(config, fd)
        print('No configuration file was found for arellepy or configuration file is invalid, a new file was created and needs to be configured as follows:\n'
                '"srcDir" enter path to local clone of arelle git\n'
                '"appDir" enter path to local installation of arelle\n'
                '"env" which env to use src/app (if left empty and both app and src paths are entered app path will be used as default)\n'
                'At least one valid "src" or "app" must be entered to be able to import arellepy')

    return config


def selectRunEnv(env, workingDir=None, appDir=None, srcDir=None):
    """Conveniently sets environment variables based on whether runing from app or source.

    The is function makes the appropriate changes to cwd and path for runing from installed
    arelle app or src, in case of app it tries to memic app environment, usually using py35embd
    and only installed app's frozen libs are used except sys and os. it makes the necessary changes
    to path, cwd to run code from source or installed arelle app.

    Arguments:
        env {str} -- either "src" or "app"
        workingDir {str} -- location of my workings (modules used in the run)

    Keyword Arguments:
        appDir {str} -- path to installed app dir (default: {None})
        srcDir {[type]} -- path to source dir (default: {None})

    Returns:
        A string representing the path for the resouces dir used by the Cntlr

    Raises:
        Exception: when nothing is selected
    """
    if not any([appDir, srcDir]):
        raise Exception("""Input a valid path to either arelle installation dir 'appDir' or
    a valid path to arelle source dir 'srcDir'""")
    else:
        if env == "src":
            if not srcDir or not os.path.exists(srcDir):
                raise Exception("srcDir:{} does not exist".format(srcDir))
            else:
                # setup appropriate sys.path entries
                myPaths = [
                    srcDir, # Target source dir
                    os.path.join(srcDir, "arelle"), # arelle package dir
                    os.path.join(srcDir, "arelle/plugin"), # plugins dir in source
                    workingDir if workingDir else os.getcwd() # workings dir containing any additional modules to include
                    ]
                # Add myPaths to sys.path
                for p in myPaths:
                    if p not in sys.path:
                        sys.path.append(p)
                # set root for resource dir to be used by Cntlr module
                targetResDir = os.path.join(srcDir, "arelle")
        elif env == "app":
            if not appDir or not os.path.exists(appDir):
                raise Exception("appDir:{} does not exist".format(appDir))
            else:
                appPaths = [
                    appDir,
                    os.path.join(appDir, "lib"),
                    os.path.join(appDir, "plugin"),
                    os.path.join(appDir, "lib/library.zip"),
                    # # Might be needed to launch GUI (see env vars below)
                    # os.path.join(appDir, "tcl"),
                    # os.path.join(appDir, "tk")
                    workingDir if workingDir else os.getcwd() # workings dir containing any additional modules to include
                ]
                # Change current wd to app directory
                warnings.warn("Changing working directory to {}".format(appDir), CntlrPyWarning)
                os.chdir(appDir)
                # Add appPaths to sys.path
                for p in appPaths:
                    if p not in sys.path:
                        sys.path.append(p)
                # # TK and TCL env vars are need to accommodate launching arelle GUI from python
                # # TK/TCL env vars provides path to libs, note that tk and tcl DLLs must be in
                # # the current working directory when on execution 
                # # This changed in recent versions
                # os.environ["TCL_LIBRARY"] = os.path.join(appDir, 'tcl')
                # os.environ["TK_LIBRARY"] = os.path.join(appDir, 'tk')

                # set root for resource dir to be used by Cntlr module
                targetResDir = appDir
        else:
            raise Exception("Set env to either 'src' or 'app'!")
    return targetResDir

def xmlFileFromString(xmlString, temp=True, filepath=None, filePrefix=None, identifier=None, tempDir=None, deleteF=True):
    '''Returns a file or tempfile handle for the xml string to be used later with arelle
    if 'temp' is False, a filePath must be entered, xmlString will be written to that file and will REPLACE it if it exists,
    if 'temp' is True, a temporary file will be written to 'tempDir' (or system default temporary dir if tempDir=None).
    'filePrefix', 'identifier' are used with to construct temp file name, ignored if 'temp' is False.
    '''
    # first try to parse the string
    _xml = etree.fromstring(xmlString).getroottree()
    xmlString = etree.tostring(_xml)

    fileHandle = None

    if not temp:
        # an exception will be raised if filepath is invalid
        fileHandle = open(filepath, 'wb+')
        fileHandle.write(xmlString if type(xmlString) is bytes else bytes(xmlString, encoding='utf-8'))
        fileHandle.seek(0)
    elif temp:
        if tempDir:
            if not os.path.exists(tempDir):
                raise Exception('"{}" does not exist'.format(tempDir))
        else:
            tempDir = tempfile.gettempdir()

        fileNamePrefix = filePrefix if filePrefix else 'arellepy_'
    
        if identifier:
            fileNamePrefix += 'id_' + str(identifier) + '_' + datetime.now().strftime("%Y%m%d%H%M%S%f") + '_'
        else:
            fileNamePrefix += 'on_' + datetime.now().strftime("%Y%m%d%H%M%S%f") + '_'

        tempFormulaFile = tempfile.NamedTemporaryFile(prefix=fileNamePrefix, suffix='.xml', dir=tempDir, delete=deleteF)
        tempFormulaFile.write(xmlString if type(xmlString) is bytes else bytes(xmlString, 'utf-8'))
        tempFormulaFile.seek(0)
        fileHandle = tempFormulaFile
    
    return fileHandle

        
def getExtractedXbrlInstance(url):
    '''Gets the url of extracted XBRL instance from the url of inlineXBRL form, used when XBRL instance is needed while inlineXBRL is reported'''
    _url = url.url if type(url).__name__ == 'ModelRssItem' else url
    res_url = None
    # first guess url of extracted document
    url_i = os.path.splitext(_url)[0] + '_htm.xml'
    n = 0
    while not res_url and n<=3:
        try:
            test = request.urlopen(url_i)
            if test.code == 200:
                res_url = url_i
        except:
            pass
        time.sleep(1)
   # if not found get it from index page
    if not res_url:
        try:
            # parse index page
            index = url.find('link').text
            page = request.urlopen(index)
            tree = html.parse(page)
            extractedPath = tree.xpath('.//table[contains(@summary, "Data Files")]//*[contains(text(), "EXTRACTED")]/ancestor::tr/td[3]//@href')[0]
            # urlParts = parse.urlparse(index)
            # extractedInstanceUrl = urlParts._replace(path= extractedPath).geturl()
            extractedInstanceUrl = parse.urljoin(index, extractedPath)
            test2 = request.urlopen(extractedInstanceUrl)
            # if test2.code == 200:
            res_url = extractedInstanceUrl
        except:
            pass
    if not res_url:
        res_url = url_i
    return res_url
        

