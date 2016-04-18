import testcases.utils.process_utils


def rpmbuildEval(macro):
    return testcases.utils.process_utils.processToString(['rpmbuild', '--eval', '%{' + macro + '}'])


def listFilesInPackage(rpmFile):
    return testcases.utils.process_utils.processAsStrings(['rpm', '-qlp', rpmFile])

def listDocsInPackage(rpmFile):
    return testcases.utils.process_utils.processAsStrings(['rpm', '-qldp', rpmFile])

def listConfigFilesInPackage(rpmFile):
    return testcases.utils.process_utils.processAsStrings(['rpm', '-qlcp', rpmFile])

def listOfRequires(rpmFile):
    return testcases.utils.process_utils.processAsStrings(['rpm', '--requires',  '-qp', rpmFile])

def listOfProvides(rpmFile):
    return testcases.utils.process_utils.processAsStrings(['rpm', '--provides',  '-qp', rpmFile])

def listOfObsoletes(rpmFile):
    return testcases.utils.process_utils.processAsStrings(['rpm', '--obsoletes',  '-qp', rpmFile])

def listOfVersionlessRequires(rpmFile):
    return _filterVersions(listOfRequires(rpmFile))

def listOfVersionlessProvides(rpmFile):
    return _filterVersions(listOfProvides(rpmFile))

def listOfVersionlessObsoletes(rpmFile):
    return _filterVersions(listOfObsoletes(rpmFile))


def _filterVersions(listOfStrings):
    filtered = []
    for orig in listOfStrings:
        filtered.append(orig.split()[0])
    return filtered

def _isScripletLine(scriplet, line):
    return line.startswith(scriplet + " " + ScripletStarterFinisher.scriptlet)

class ScripletStarterFinisher:
    #hard to say when rpm uses uninstall or jsut un or install or just "nothing"
    allScriplets = [
        'pretrans',
        'preinstall',
        'postinstall',
        'triggerinstall',
        'triggeuninstall',
        'preuninstall',
        'postuninstall',
        'triggerpostuninstall',
        'posttrans'
    ]

    scriptlet = "scriptlet"

    def __init__(self, id):
        self.id = id;

    def start(self, line):
        return _isScripletLine(self.id, line)

    def stop(self, line):
        for scriptlet in  ScripletStarterFinisher.allScriplets:
            if _isScripletLine(scriptlet, line):
                return False #stop
        return True #continue

def getSrciplet(rpmFile, scripletId):
    sf = ScripletStarterFinisher(scripletId)
    return testcases.utils.process_utils.processAsStrings(['rpm', '-qp', '--scripts', rpmFile], sf.start, sf.stop, False)