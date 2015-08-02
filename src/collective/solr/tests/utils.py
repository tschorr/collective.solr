import json
from os.path import dirname, join
from httplib import HTTPConnection
from threading import Thread
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from socket import error
from sys import stderr
from re import search
from scorched.connection import SolrConnection
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
    return open(filename, 'r').read().strip()


def fakesolrconnection(solrconn, schema=None, fakedata=[], orig=None):
    """ helper function to set up a fake solr api on a SolrConnection """
    output = []

    class FakeSolrConnection(SolrConnection):
        _schema = None

        def __init__(self, fakedata=[], orig=None):
            self.fakedata = fakedata
            self.orig = orig

        def update(self, update_doc, **kwargs):
            output.append(update_doc)

        def select(self, params):
            output.append(('select', params))
            return self.fakedata.pop(0)

        def __getattr__(self, name):
            if self.orig:
                return getattr(self.orig, name)
            else:
                raise AttributeError(name)

        # def search(self, *args, **kwargs):
        #     output.append(('search', (args, kwargs)))
        #     if self.schema:
        #         datefields = tuple(self._extract_datefields(self.schema))
        #     else:
        #         datefields = tuple()
        #     return SolrResponse.from_json(
        #         self.fakedata.pop(0),
        #         datefields=datefields
        #     )
    solrconn.api.conn = FakeSolrConnection(fakedata, orig=solrconn.api.conn)

    if schema:
        if isinstance(schema, basestring):
            schema = json.loads(schema)

        def init_schema():
            output.append(('schema', schema))
            return schema
        solrconn.api.init_schema = init_schema
    return output


def fakemore(solrconn, *fakedata):
    """ helper function to add more fake http requests to a SolrConnection """
    assert hasattr(solrconn.api.conn, 'fakedata')
    solrconn.api.conn.fakedata.extend(fakedata)


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
