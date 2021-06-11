## About
This [**Arelle**](https://github.com/Arelle/Arelle) plugin is a personal project just to make my life easier while working with submissions made to SEC in XBRL format, this plugin is independent form the main Arelle project.  

The purpose of this plugin/module is to provide an entry point to Arelle (as locally installed app or local repo) and and use its components as if it was a python package. Also it helps in using Arelle in an interactive environment such as Jupyter notebook to be able to inspect its object and extract data. The Python API in [Arelle Documentation](https://arelle.org/arelle/documentation/api/) has some guidance on how to use Arelle classes and methods. While currently there are few [arelle package based package on Pypi](https://pypi.org/search/?q=arelle) those packages do not seem to be maintained and kept up to date with the main Arelle project.

This plugin provides an entry point to Arelle from local Arelle source code or Arelle app installation by setting up the current working environment to locate Arelle files, that way all the updates and changes to the main Arelle projects are readily available. Also provides few other functions and classes that I find useful for what I do.

## Installation
* If using Arelle from source, then copy to `~/Arelle/arelle/plugin/arellepy`  
* If using Arelle application, then copy to `~/Arelle/plugin/arellepy`

A config file must be setup at `~/Arelle/arelle/plugin/arellepy/arellepyConfig.json` to tell the plugin which files to use as follows:
```js
{
   // at least one of "srcDir" or "appDir" is required 
    "srcDir": "/path/to/Arelle/local/repo", //This is the path to local copy of arelle repository (running from source)
    "appDir": "/path/to/Arelle/App", //This is the path to local installation of Arelle application
    "env":"app" //tell the plugin what to use, either "app" or "src", this will have an effect only if we are running our own scripts, has no effect if we are running the app
}
```

**If using from source, make sure that all python package that Arelle depends on are installed in the python environment.**  
**If using from app, python major version must match Arelle's python version**

## Usage

Importing from arelle
```python
# first thing we need to append arellepy to path
import sys
sys.path.append('/path/to/arellepy/')
import arellepy
# now we should have access to Arelle components 
# Note: if we are using Arelle App installation, python version used must match that of Arelle app 
from arelle.Cntlr import Cntlr
```

Using objects from arellepy
```python

>>> import sys
>>> sys.path.append('/path/to/arellepy/')
>>> import arellepy
>>> # import CntlrPy class
>>> from arellepy.CntlrPy import CntlrPy
>>> # config
>>> conf = 'path/to/config/folder' # folder containing Arelle runtime configurations and web cache
>>> # initialize Cntlr 
>>> cntlr = CntlrPy(
...     instConfigDir=conf,
...     logFileName="logToBuffer",
...     preloadPlugins='rssDB|validate/EFM|EdgarRenderer|transforms/SEC'
... )
>>> # Get help on run options
>>> cntlr.OptionsHandler.optHelp(searchRE='file')

Search Items:
--------------
--file (kwarg=file): (Source - CntlrCmdLine)
FILENAME is an entry point, which may be an XBRL instance, schema, linkbase file, inline XBRL instance, testcase file, testcase index file.  FILENAME may be a local file or a URI to a web located file.  For multiple instance filings may be | separated file names or JSON list of file/parameter dicts [{"file":"filepath"}, {"file":"file2path"} ...].
action: {'store'}
dest: {'entrypointFile'}

>>> # load an instance
>>> f = 'https://www.sec.gov/Archives/edgar/data/789019/000156459017000654/0001564590-17-000654-xbrl.zip'
>>> cntlr.runKwargs(file= f)
>>> type(cntlr)
<class 'arellepy.CntlrPy.CntlrPy'>
>>> cntlr.modelManager.modelXbrl.factsInInstance.__len__()
1749
```
Using another utility:

```python
>>> import sys
>>> sys.path.append('/path/to/arellepy/')
>>> # import from arellepy
>>> from arellepy.CntlrPy import arelleCmdLineRun
>>> # `arelleCmdLineRun` function return a arelleCmdLine controller object after running 
>>> # all the arguments entered exactly as entered in arelleCmdLine 
>>> conf = '/path/to/desired/Configuration/Folder' # folder containing cache and arelle runtime configurations
>>> args = '-f https://www.sec.gov/Archives/edgar/data/789019/000156459017000654/0001564590-17-000654-xbrl.zip --logFile logToPrint'
>>> cmdCntlr = arelleCmdLineRun(args, configDir=conf)
[info] loaded in 13.34 secs at 2021-06-11T12:05:29 - https://www.sec.gov/Archives/edgar/data/789019/000156459017000654/0001564590-17-000654-xbrl.zip/msft-20161231.xml
>>> type(cmdCntlr)
<class 'arelle.CntlrCmdLine.CntlrCmdLine'>
>>> cmdCntlr.modelManager.modelXbrl.facts.__len__()
1749
```
**DISCLAIMER:** The code in this project was created for research and personal use purposes **ONLY**, is provided as is without any guarantees or implied or express warranties. This project depends and uses code from [Arelle project](https://github.com/Arelle/Arelle) but is NOT a part of that project.

### License
This project is licensed under same license, terms and conditions for [Arelle License](https://github.com/selgamal/Arelle/blob/master/License.txt), in addition to any terms, conditions, notices and disclaimers in this document.  


