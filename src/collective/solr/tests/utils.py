from os.path import dirname, join
from httplib import HTTPConnection
from threading import Thread
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from StringIO import StringIO
from socket import error
from sys import stderr
from re import search

from collective.solr.local import getLocal, setLocal
from collective.solr import tests

try:
    from zope.component.hooks import getSite, setSite
except ImportError:
    from zope.app.component.hooks import getSite, setSite

try:
    from Zope2.App import zcml
except ImportError:
    from Products.Five import zcml


def loadZCMLString(string):
    # Unset current site for Zope 2.13
    saved = getSite()
    setSite(None)
    try:
        zcml.load_string(string)
    finally:
        setSite(saved)


def getData(filename):
    """ return a file object from the test data folder """
    filename = join(dirname(tests.__file__), 'data', filename)
    return open(filename, 'r').read()


def fakesolrinterface(solrconn, schema=None, fakedata=[]):
    """ helper function to set up a fake solr api on a SolrConnection """
    output = []

    class FakeHTTPSolrInterface:
        _schema = None

        def __init__(self, fakedata=[]):
            self.fakedata = fakedata

        @property
        def schema(self):
            output.append(('schema', self._schema))
            return self._schema

        def add(self, docs):
            output.append(('add', docs))

        def delete_by_ids(self, ids):
            output.append(('delete_by_ids', ids))

        def commit(self):
            output.append(('commit', None))

    solrconn.conn = FakeHTTPSolrInterface(fakedata)
    if schema:
        if isinstance(schema, basestring):
            schema = json.loads(schema)
        solrconn.conn._schema = schema
    return output


# OBSOLETED
def fakehttp(solrconn, *fakedata):
    """ helper function to set up a fake http request on a SolrConnection """

    class FakeOutput(list):

        """ helper class to organize output from fake connections """

        conn = solrconn

        def log(self, item):
            self.current.append(item)

        def get(self, skip=0):
            self[:] = self[skip:]
            return ''.join(self.pop(0)).replace('\r', '')

        def new(self):
            self.current = []
            self.append(self.current)

        def __len__(self):
            self.conn.flush()   # send out all pending xml
            return super(FakeOutput, self).__len__()

        def __str__(self):
            self.conn.flush()   # send out all pending xml
            if self:
                return ''.join(self[0]).replace('\r', '')
            else:
                return ''

    output = FakeOutput()

    class FakeSocket(StringIO):

        """ helper class to fake socket communication """

        def sendall(self, str):
            output.log(str)

        def makefile(self, mode, name):
            return self

        def read(self, amt=None):
            if self.closed:
                return ''
            return StringIO.read(self, amt)

        def readline(self, length=None):
            if self.closed:
                return ''
            return StringIO.readline(self, length)

    class FakeHTTPConnection(HTTPConnection):

        """ helper class to fake a http connection object from httplib.py """

        def __init__(self, host, *fakedata):
            HTTPConnection.__init__(self, host)
            self.fakedata = list(fakedata)

        def putrequest(self, *args, **kw):
            response = self.fakedata.pop(0)     # get first response
            self.sock = FakeSocket(response)    # and set up a fake socket
            output.new()                        # as well as an output buffer
            HTTPConnection.putrequest(self, *args, **kw)

        def setTimeout(self, timeout):
            pass

    solrconn.conn = FakeHTTPConnection(solrconn.conn.host, *fakedata)
    return output


def fakemore(solrconn, *fakedata):
    """ helper function to add more fake http requests to a SolrConnection """
    assert hasattr(solrconn.conn, 'fakedata')   # `isinstance()` doesn't work?
    solrconn.conn.fakedata.extend(fakedata)


def fakeServer(actions, port=55555):
    """ helper to set up and activate a fake http server used for testing
        purposes; <actions> must be a list of handler functions, which will
        receive the base handler as their only argument and are used to
        process the incoming requests in turn; returns a thread that should
        be 'joined' when done """
    class Handler(BaseHTTPRequestHandler):

        def do_POST(self):
            action = actions.pop(0)             # get next action
            action(self)                        # and process it...

        def do_GET(self):
            action = actions.pop(0)             # get next action
            action(self)                        # and process it...

        def log_request(*args, **kw):
            pass

    def runner():
        while actions:
            server.handle_request()
    server = HTTPServer(('', port), Handler)
    thread = Thread(target=runner)
    thread.start()
    return thread


def pingSolr():
    """ test if the solr server is available """
    status = getLocal('solrStatus')
    if status is not None:
        return status
    conn = HTTPConnection('localhost', 8983)
    try:
        conn.request('GET', '/solr/admin/ping')
        response = conn.getresponse()
        status = response.status == 200
        msg = "INFO: solr return status '%s'" % response.status
    except error, e:
        status = False
        msg = 'WARNING: solr tests could not be run: "%s".' % e
    if not status:
        print >> stderr
        print >> stderr, '*' * len(msg)
        print >> stderr, msg
        print >> stderr, '*' * len(msg)
        print >> stderr
    setLocal('solrStatus', status)
    return status


def numFound(result):
    match = search(r'numFound="(\d+)"', result)
    if match is not None:
        match = int(match.group(1))
    return match


# https://github.com/hay/xml2json

"""xml2json.py  Convert XML to JSON

Relies on ElementTree for the XML parsing.  This is based on
pesterfish.py but uses a different XML->JSON mapping.
The XML->JSON mapping is described at
http://www.xml.com/pub/a/2006/05/31/converting-between-xml-and-json.html

Rewritten to a command line utility by Hay Kranen < github.com/hay > with
contributions from George Hamilton (gmh04) and Dan Brown (jdanbrown)

XML                              JSON
<e/>                             "e": null
<e>text</e>                      "e": "text"
<e name="value" />               "e": { "@name": "value" }
<e name="value">text</e>         "e": { "@name": "value", "#text": "text" }
<e> <a>text</a ><b>text</b> </e> "e": { "a": "text", "b": "text" }
<e> <a>text</a> <a>text</a> </e> "e": { "a": ["text", "text"] }
<e> text <a>text</a> </e>        "e": { "#text": "text", "a": "text" }

This is very similar to the mapping used for Yahoo Web Services
(http://developer.yahoo.com/common/json.html#xml).

This is a mess in that it is so unpredictable -- it requires lots of testing
(e.g. to see if values are lists or strings or dictionaries).  For use
in Python this could be vastly cleaner.  Think about whether the internal
form can be more self-consistent while maintaining good external
characteristics for the JSON.

Look at the Yahoo version closely to see how it works.  Maybe can adopt
that completely if it makes more sense...

R. White, 2006 November 6
"""

import json
import optparse
import sys

import xml.etree.cElementTree as ET


def strip_tag(tag):
    strip_ns_tag = tag
    split_array = tag.split('}')
    if len(split_array) > 1:
        strip_ns_tag = split_array[1]
        tag = strip_ns_tag
    return tag


def elem_to_internal(elem, strip_ns=1, strip=1):
    """Convert an Element into an internal dictionary (not JSON!)."""

    d = {}
    elem_tag = elem.tag
    if strip_ns:
        elem_tag = strip_tag(elem.tag)
    else:
        for key, value in list(elem.attrib.items()):
            d['@' + key] = value

    # loop over subelements to merge them
    for subelem in elem:
        v = elem_to_internal(subelem, strip_ns=strip_ns, strip=strip)

        tag = subelem.tag
        if strip_ns:
            tag = strip_tag(subelem.tag)

        value = v[tag]

        try:
            # add to existing list for this tag
            d[tag].append(value)
        except AttributeError:
            # turn existing entry into a list
            d[tag] = [d[tag], value]
        except KeyError:
            # add a new non-list entry
            d[tag] = value
    text = elem.text
    tail = elem.tail
    if strip:
        # ignore leading and trailing whitespace
        if text:
            text = text.strip()
        if tail:
            tail = tail.strip()

    if tail:
        d['#tail'] = tail

    if d:
        # use #text element if other attributes exist
        if text:
            d["#text"] = text
    else:
        # text is the value if no attributes
        d = text or None
    return {elem_tag: d}


def internal_to_elem(pfsh, factory=ET.Element):

    """Convert an internal dictionary (not JSON!) into an Element.

    Whatever Element implementation we could import will be
    used by default; if you want to use something else, pass the
    Element class as the factory parameter.
    """

    attribs = {}
    text = None
    tail = None
    sublist = []
    tag = list(pfsh.keys())
    if len(tag) != 1:
        raise ValueError("Illegal structure with multiple tags: %s" % tag)
    tag = tag[0]
    value = pfsh[tag]
    if isinstance(value, dict):
        for k, v in list(value.items()):
            if k[:1] == "@":
                attribs[k[1:]] = v
            elif k == "#text":
                text = v
            elif k == "#tail":
                tail = v
            elif isinstance(v, list):
                for v2 in v:
                    sublist.append(internal_to_elem({k: v2}, factory=factory))
            else:
                sublist.append(internal_to_elem({k: v}, factory=factory))
    else:
        text = value
    e = factory(tag, attribs)
    for sub in sublist:
        e.append(sub)
    e.text = text
    e.tail = tail
    return e


def elem2json(elem, options, strip_ns=1, strip=1):

    """Convert an ElementTree or Element into a JSON string."""

    if hasattr(elem, 'getroot'):
        elem = elem.getroot()

    if options.pretty:
        return json.dumps(elem_to_internal(elem, strip_ns=strip_ns, strip=strip), sort_keys=True, indent=4, separators=(',', ': '))
    else:
        return json.dumps(elem_to_internal(elem, strip_ns=strip_ns, strip=strip))


def json2elem(json_data, factory=ET.Element):

    """Convert a JSON string into an Element.

    Whatever Element implementation we could import will be used by
    default; if you want to use something else, pass the Element class
    as the factory parameter.
    """

    return internal_to_elem(json.loads(json_data), factory)


def xml2json(xmlstring, options, strip_ns=1, strip=1):

    """Convert an XML string into a JSON string."""

    elem = ET.fromstring(xmlstring)
    return elem2json(elem, options, strip_ns=strip_ns, strip=strip)


def json2xml(json_data, factory=ET.Element):

    """Convert a JSON string into an XML string.

    Whatever Element implementation we could import will be used by
    default; if you want to use something else, pass the Element class
    as the factory parameter.
    """
    if not isinstance(json_data, dict):
        json_data = json.loads(json_data)

    elem = internal_to_elem(json_data, factory)
    return ET.tostring(elem)

'''
def main():
    p = optparse.OptionParser(
        description='Converts XML to JSON or the other way around.  Reads from standard input by default, or from file if given.',
        prog='xml2json',
        usage='%prog -t xml2json -o file.json [file]'
    )
    p.add_option('--type', '-t', help="'xml2json' or 'json2xml'", default="xml2json")
    p.add_option('--out', '-o', help="Write to OUT instead of stdout")
    p.add_option(
        '--strip_text', action="store_true",
        dest="strip_text", help="Strip text for xml2json")
    p.add_option(
        '--pretty', action="store_true",
        dest="pretty", help="Format JSON output so it is easier to read")
    p.add_option(
        '--strip_namespace', action="store_true",
        dest="strip_ns", help="Strip namespace for xml2json")
    p.add_option(
        '--strip_newlines', action="store_true",
        dest="strip_nl", help="Strip newlines for xml2json")
    options, arguments = p.parse_args()

    inputstream = sys.stdin
    if len(arguments) == 1:
        try:
            inputstream = open(arguments[0])
        except:
            sys.stderr.write("Problem reading '{0}'\n".format(arguments[0]))
            p.print_help()
            sys.exit(-1)

    input = inputstream.read()

    strip = 0
    strip_ns = 0
    if options.strip_text:
        strip = 1
    if options.strip_ns:
        strip_ns = 1
    if options.strip_nl:
        input = input.replace('\n', '').replace('\r','')
    if (options.type == "xml2json"):
        out = xml2json(input, options, strip_ns, strip)
    else:
        out = json2xml(input)

    if (options.out):
        file = open(options.out, 'w')
        file.write(out)
        file.close()
    else:
        print(out)
'''
