# This software and any associated files are copyright 2010 Brian Carver and
# Michael Lissner.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  Under Sections 7(a) and 7(b) of version 3 of the GNU Affero General Public
#  License, that license is supplemented by the following terms:
#
#  a) You are required to preserve this legal notice and all author
#  attributions in this program and its accompanying documentation.
#
#  b) You are prohibited from misrepresenting the origin of any material
#  within this covered work and you are required to mark in reasonable
#  ways how any modified versions differ from the original version.
import sys
sys.path.append('/var/www/court-listener/alert')
sys.path.append('/home/mlissner/FinalProject/alert')

from alert import settings
from django.core.management import setup_environ
setup_environ(settings)

from alertSystem.models import *
from lib.string_utils import *

from django.core.files.base import ContentFile

import hashlib
import logging
import logging.handlers
import StringIO
import subprocess
import time
import urllib2


LOG_FILENAME = '/var/log/scraper/daemon_log.out'

# Set up a specific logger with our desired output level
logger = logging.getLogger('Logger')
logger.setLevel(logging.DEBUG)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(
              LOG_FILENAME, maxBytes=5120000, backupCount=1)

logger.addHandler(handler)


class makeDocError(Exception):
    '''
    This is a simple class for errors stemming from the makeDocFromURL function.
    It doesn't do much except to make the code a little cleaner and more precise.
    '''
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def readURL(url, courtID):
    try: html = urllib2.urlopen(url).read()
    except urllib2.HTTPError, e:
        print "****ERROR CONNECTING TO COURT: " + str(courtID) + "****"
        print 'HTTPError = ' + str(e.code)
    except urllib2.URLError, e:
        print "****ERROR CONNECTING TO COURT: " + str(courtID) + "****"
        print 'URLError = ' + str(e.reason)
    except httplib.HTTPException, e:
        print "****ERROR CONNECTING TO COURT: " + str(courtID) + "****"
        print 'HTTPException'
    except Exception:
        print "****ERROR CONNECTING TO COURT: " + str(courtID) + "****"
        print 'Generic Exception: ' + traceback.format_exc()
    return html


def printAndLogNewDoc(VERBOSITY, ct, cite):
    '''
    Simply prints the log message and then logs it.
    '''
    caseName = str(cite)
    caseNumber = str(cite.caseNumber)
    if VERBOSITY >= 1:
        print time.strftime("%a, %d %b %Y %H:%M", time.localtime()) + \
            ": Added " + ct.courtShortName + ": " + unicode(caseName, errors='ignore') + \
            ", " + caseNumber
    logger.debug(time.strftime("%a, %d %b %Y %H:%M", time.localtime()) +
        ": Added " + ct.courtShortName + ": " + unicode(caseName, errors='ignore') + \
        ", " + caseNumber)


def makeDocFromURL(LinkToDoc, ct):
    '''
    Receives a URL and a court as arguments, then downloads the Doc
    that's in it, and makes it into a StringIO. Generates a sha1 hash of the
    file, and tries to add it to the db. If it's a duplicate, it gets the one in
    the DB. If it's a new sha1, it creates a new document.

    returns a StringIO of the PDF, a Document object, and a boolean indicating
    whether the Document was created
    '''

    # get the Doc
    try:
        webFile = urllib2.urlopen(LinkToDoc)
        stringThing = StringIO.StringIO()
        stringThing.write(webFile.read())
        myFile = ContentFile(stringThing.getvalue())
        webFile.close()
    except:
        err = 'DownloadingError: ' + str(LinkToDoc)
        raise makeDocError(err)

    # make the SHA1
    data = myFile.read()

    # test for empty files (thank you CA1)
    if len(data) == 0:
        err = "EmptyFileError: " + str(LinkToDoc)
        raise makeDocError(err)

    sha1Hash = hashlib.sha1(data).hexdigest()

    # using that, we check for a dup
    doc, created = Document.objects.get_or_create(documentSHA1 = sha1Hash,
        court = ct)

    if created:
        # we only do this if it's new
        doc.documentSHA1 = sha1Hash
        doc.download_URL = LinkToDoc
        doc.court = ct
        doc.source = "C"

    return myFile, doc, created



def courtChanged(url, contents):
    '''
    Takes HTML contents from a court download, generates a SHA1, and then
    compares that hash to a value in the DB, if there is one. If there is a value
    and it is the same, it returns false. Else, it returns true.
    '''
    sha1Hash = hashlib.sha1(contents).hexdigest()
    url2Hash, created = urlToHash.objects.get_or_create(url=url)

    if not created and url2Hash.SHA1 == sha1Hash:
        # it wasn't created, and it has the same SHA --> not changed.
        return False
    else:
        # Whether or not it was created, it's a change, and so we update the SHA
        # and save the changes.
        url2Hash.SHA1 = sha1Hash
        url2Hash.save()

        # Log the change time and URL
        try:
            logger.debug(time.strftime("%a, %d %b %Y %H:%M", time.localtime()) + ": URL: " + url)
        except UnicodeDecodeError:
            pass

        return True


def hasDuplicate(caseNum, caseName):
    '''
    Takes a caseName and a caseNum, and checks if the object exists in the
    DB. If it doesn't, then it puts it in. If it does, it returns it.
    '''

    # data cleanup
    caseName = harmonize(clean_string(caseName))
    caseNum  = clean_string(caseNum)

    caseNameShort = trunc(caseName, 100)

    # check for duplicates, make the object in their absence
    cite, created = Citation.objects.get_or_create(
        caseNameShort = str(caseNameShort), caseNumber = str(caseNum))

    if caseNameShort == caseName:
        # no truncation.
        cite.caseNameFull = caseNameShort
    else:
        # truncation happened. Therefore, use the untruncated value as the full
        # name.
        cite.caseNameFull = caseName
    cite.save()

    return cite, created


def getDocContent(docs):
    '''
    Get the contents of a list of files, and add them to the DB, sniffing
    their mimetype.
    '''
    for doc in docs:
        path = str(doc.local_path)
        path = settings.MEDIA_ROOT + path






        mimetype = path.split('.')[-1]
        if mimetype == 'pdf':
            # do the pdftotext work for PDFs
            process = subprocess.Popen(["pdftotext", "-layout", "-enc", "UTF-8",
                path, "-"], shell=False, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            content, err = process.communicate()
            doc.documentPlainText = anonymize(content)
            if err:
                print "****Error extracting PDF text from: " + doc.citation.caseNameShort + "****"
                continue
        elif mimetype == 'txt':
            # read the contents of text files.
            try:
                content = open(path).read()
                doc.documentPlainText = anonymize(content)
            except:
                print "****Error extracting plain text from: " + doc.citation.caseNameShort + "****"
                continue
        elif mimetype == 'wpd':
            # It's a Word Perfect file. Use the wpd2html converter, clean up
            # the HTML and save the content to the HTML field.
            print "Parsing: " + path
            process = subprocess.Popen(['wpd2html', path, '-'], shell=False,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            content, err = process.communicate()

            parser = etree.HTMLParser()
            import StringIO
            tree = etree.parse(StringIO.StringIO(content), parser)
            body = tree.xpath('//body')
            content = tostring(body[0]).replace('<body>', '').replace('</body>','')

            fontsizeReg = re.compile('font-size: .*;')
            content = re.sub(fontsizeReg, '', content)

            colorReg = re.compile('color: .*;')
            content = re.sub(colorReg, '', content)

            if 'not for publication' in content.lower():
                doc.documentType = "Unpublished"
            doc.documentHTML = anonymize(content)

            if err:
                print "****Error extracting WPD text from: " + doc.citation.caseNameShort + "****"
                continue
        else:
            print "*****Unknown mimetype. Unable to parse: " + doc.citation.caseNameShort + "****"
            continue

        try:
            doc.save()
        except Exception, e:
            print "****Error saving text to the db for: " + doc.citation.caseNameShort + "****"
