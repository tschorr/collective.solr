from unittest import TestCase, defaultTestLoader
from threading import Thread
from re import search, findall, DOTALL
from DateTime import DateTime
from datetime import datetime
from datetime import date
from zope.component import provideUtility
from zope.interface import implements
from Products.CMFCore.CMFCatalogAware import CMFCatalogAware

from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.interfaces import ICheckIndexable
from collective.solr.manager import SolrConnectionConfig
from collective.solr.manager import SolrConnectionManager
from collective.solr.indexer import SolrIndexProcessor
from collective.solr.indexer import logger as logger_indexer
from collective.solr.tests.utils import getData
# from collective.solr.tests.utils import fakehttp
from collective.solr.tests.utils import fakesolrconnection
from collective.solr.tests.utils import fakemore
from collective.solr.solr import SolrConnection
from collective.solr.utils import prepareData


class Foo(CMFCatalogAware):

    """ dummy test object """

    implements(ICheckIndexable)

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)

    def __call__(self):
        return True


def sortFields(output):
    """ helper to sort `<field>` tags in output for testing """
    pattern = r'^(.*<doc>)(<field .*</field>)(</doc>.*)'
    prefix, fields, suffix = search(pattern, output, DOTALL).groups()
    tags = r'(<field [^>]*>[^<]*</field>)'
    return prefix + ''.join(sorted(findall(tags, fields))) + suffix


class QueueIndexerTests(TestCase):

    def setUp(self):
        provideUtility(SolrConnectionConfig(), ISolrConnectionConfig)
        self.mngr = SolrConnectionManager()
        self.mngr.setHost(active=True)
        conn = self.mngr.getConnection()
        fakesolrconnection(conn, schema=getData('schema.json'))  # fake schema
        self.mngr.getSchema()                       # read and cache the schema
        self.proc = SolrIndexProcessor(self.mngr)

    def tearDown(self):
        self.mngr.closeConnection()
        self.mngr.setHost(active=False)

    def testPrepareData(self):
        data = {'allowedRolesAndUsers': [
            'user:test_user_1_', 'user:portal_owner']}
        prepareData(data)
        self.assertEqual(
            data,
            {
                'allowedRolesAndUsers': [
                    'user$test_user_1_',
                    'user$portal_owner'
                ]
            }
        )

    def testLanguageParameterHandling(self):
        # empty strings are replaced...
        data = {'Language': ['en', '']}
        prepareData(data)
        self.assertEqual(data, {'Language': ['en', 'any']})
        data = {'Language': ''}
        prepareData(data)
        self.assertEqual(data, {'Language': 'any'})
        # for other indices this shouldn't happen...
        data = {'Foo': ['en', '']}
        prepareData(data)
        self.assertEqual(data, {'Foo': ['en', '']})

    def testIndexObject(self):
        response = getData('add_response.txt')
        # fake add response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        # indexing sends data
        self.proc.index(Foo(id='500', name='python test doc'))
        # committing sends data
        self.proc.commit()
        self.assertEqual(output[0].count('"add":'), 1)
        self.assertEqual(output[0].count('"name": "python test doc"'), 1)
        self.assertEqual(output[0].count('"id": "500"'), 1)
        # self.assertEqual(sortFields(str(output)), getData('add_request.txt'))

    def testIndexAccessorRaises(self):
        response = getData('add_response.txt')
        # fake add response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )

        def brokenfunc():
            raise ValueError
        self.proc.index(Foo(id='500', name='python test doc',
                            text=brokenfunc))   # indexing sends data
        # committing sends data
        self.proc.commit()
        self.assertEqual(output[0].count('"add":'), 1)
        self.assertEqual(output[0].count('"name": "python test doc"'), 1)
        self.assertEqual(output[0].count('"id": "500"'), 1)
        # self.assertEqual(sortFields(str(output)), getData('add_request.txt'))

    def testPartialIndexObject(self):
        foo = Foo(id='500', name='foo', price=42.0)
        # first index all attributes...
        response = getData('add_response.txt')
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        self.proc.index(foo)
        # committing sends data
        self.proc.commit()
        self.assert_(str(output).find(
            '"price": 42.0') > 0, '"price" data not found')
        # then only a subset...
        response = getData('add_response.txt')
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        self.proc.index(foo, attributes=['id', 'name'])
        # committing sends data
        self.proc.commit()
        output = str(output)
        self.assert_(
            output.find('"name": "foo"') > 0,
            '"name" data not found'
        )
        # at this point we'd normally check for a partial update:
        #   self.assertEqual(output.find('price'), -1, '"price" data found?')
        #   self.assertEqual(output.find('42'), -1, '"price" data found?')
        # however, until SOLR-139 has been implemented (re)index operations
        # always need to provide data for all attributes in the schema...

    def testDateIndexing(self):
        foo = Foo(id='zeidler', name='andi', cat='nerd',
                  timestamp=DateTime('May 11 1972 03:45 GMT'))
        response = getData('add_response.txt')
        # fake add response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        self.proc.index(foo)
        # committing sends data
        self.proc.commit()
        self.assertEqual(str(output).count('"add":'), 1)
        required = '"timestamp": "1972-05-11T03:45:00.000Z"'
        self.assert_(str(output).find(required) > 0, '"date" data not found')

    def testDateIndexingWithPythonDateTime(self):
        foo = Foo(id='gerken', name='patrick', cat='nerd',
                  timestamp=datetime(1980, 9, 29, 14, 02))
        response = getData('add_response.txt')
        # fake add response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        self.proc.index(foo)
        # committing sends data
        self.proc.commit()
        self.assertEqual(str(output).count('"add":'), 1)
        required = '"timestamp": "1980-09-29T14:02:00.000Z"'
        self.assert_(str(output).find(required) > 0, '"date" data not found')

    def testDateIndexingWithPythonDate(self):
        foo = Foo(id='brand', name='jan-carel',
                  cat='nerd', timestamp=date(1982, 8, 05))
        response = getData('add_response.txt')
        # fake add response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        self.proc.index(foo)
        # committing sends data
        self.proc.commit()
        self.assertEqual(str(output).count('"add":'), 1)
        required = '"timestamp": "1982-08-05T00:00:00.000Z"'
        self.assert_(str(output).find(required) > 0, '"date" data not found')

    def testReindexObject(self):
        response = getData('add_response.txt')
        # fake add response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        # reindexing sends data (???)
        self.proc.reindex(Foo(id='500', name='python test doc'))
        # committing sends data
        self.proc.commit()
        self.assertEqual(output[0].count('"name": "python test doc"'), 1)
        self.assertEqual(output[0].count('"id": "500"'), 1)

    def testUnindexObject(self):
        response = getData('delete_response.txt')
        # fake response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        # unindexing sends data (???)
        self.proc.unindex(Foo(id='500', name='python test doc'))
        # committing sends data
        self.proc.commit()
        self.assertEqual(output, ['{"delete": {"id": "500"},"commit": {}}'])

    def testCommit(self):
        response = getData('commit_response.txt')
        # fake response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        # committing sends data
        self.proc.commit()
        # self.assertEqual(str(output), getData('commit_request.txt'))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0], '{"commit": {}}')

    def testNoIndexingWithoutAllRequiredFields(self):
        response = getData('dummy_response.txt')
        # fake add response
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        self.proc.index(Foo(id='500'))
        self.assertEqual(output, [])
        # committing sends data
        self.proc.commit()
        self.assertEqual(output, ['{"commit": {}}'])

    def testIndexerMethods(self):
        class Bar(Foo):

            def cat(self):
                return 'nerd'

            def price(self):
                raise AttributeError('price')
        foo = Bar(id='500', name='foo')
        # raising the exception should keep the attribute from being indexed
        response = getData('add_response.txt')
        output = fakesolrconnection(
            self.mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[response]
        )
        self.proc.index(foo)
        # committing sends data
        self.proc.commit()
        self.assertEqual(output[0].count('"add":'), 1)
        output = str(output)
        self.assertTrue(
            output.find('"cat": "nerd"') > 0,
            '"cat" data not found'
        )
        self.assertEqual(output.find('price'), -1, '"price" data found?')


class RobustnessTests(TestCase):

    def setUp(self):
        provideUtility(SolrConnectionConfig(), ISolrConnectionConfig)
        self.mngr = SolrConnectionManager()
        self.mngr.setHost(active=True)
        self.conn = self.mngr.getConnection()
        self.proc = SolrIndexProcessor(self.mngr)
        self.log = []                   # catch log messages...

        def logger(*args):
            self.log.extend(args)
        logger_indexer.warning = logger

    def tearDown(self):
        self.mngr.closeConnection()
        self.mngr.setHost(active=False)

    def testIndexingWithUniqueKeyMissing(self):
        # fake schema response
        fakesolrconnection(
            self.conn,
            schema=getData('simple_schema.json'),
        )
        # read and cache the schema
        self.mngr.getSchema()
        response = getData('add_response.txt')
        output = fakesolrconnection(
            self.conn,
            fakedata=[response]
        )
        foo = Foo(id='500', name='foo')
        # indexing sends data
        self.proc.index(foo)
        # nothing happened...
        self.assertEqual(len(output), 0)
        self.assertEqual(self.log, [
            'schema is missing unique key, skipping indexing of %r', foo])

    def testUnindexingWithUniqueKeyMissing(self):
        # fake schema response
        fakesolrconnection(
            self.conn,
            schema=getData('simple_schema.json'),
        )
        # read and cache the schema
        self.mngr.getSchema()
        response = getData('delete_response.txt')
        # fake delete response
        output = fakesolrconnection(
            self.conn,
            fakedata=[response]
        )
        foo = Foo(id='500', name='foo')
        # unindexing sends data
        self.proc.unindex(foo)
        # nothing happened...
        self.assertEqual(len(output), 0)
        self.assertEqual(self.log, [
            'schema is missing unique key, skipping unindexing of %r', foo])


class FakeHTTPConnectionTests(TestCase):

    def setUp(self):
        provideUtility(SolrConnectionConfig(), ISolrConnectionConfig)
        self.foo = Foo(id='500', name='python test doc')

    def testSingleRequest(self):
        mngr = SolrConnectionManager(active=True)
        output = fakesolrconnection(
            mngr.getConnection(),
            schema=getData('schema.json')
        )
        mngr.getSchema()
        mngr.closeConnection()
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0][0], 'schema')
        # self.failUnless(output.get().startswith(self.schema_request))

    def testTwoRequests(self):
        mngr = SolrConnectionManager(active=True)
        proc = SolrIndexProcessor(mngr)
        output = fakesolrconnection(
            mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[
                getData('add_response.txt')
            ]
        )
        proc.index(self.foo)
        mngr.closeConnection()
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0][0], 'schema')
        # BBB: closeConnection don't flush queue ...
        # self.assertEqual(len(output), 2)
        # self.failUnless(output.get().startswith(self.schema_request))
        # self.assertEqual(sortFields(output.get()),getData('add_request.txt'))

    def testThreeRequests(self):
        mngr = SolrConnectionManager(active=True)
        proc = SolrIndexProcessor(mngr)
        output = fakesolrconnection(
            mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[
                # TODO: convert http response to solr api response
                getData('add_response.txt'),
                getData('delete_response.txt')
            ]
        )
        proc.index(self.foo)
        proc.unindex(self.foo)
        mngr.closeConnection()
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0][0], 'schema')
        # BBB: closeConnection don't flush queue ...
        # self.assertEqual(len(output), 3)
        # self.failUnless(output.get().startswith(self.schema_request))
        # self.assertEqual(sortFields(output.get()),getData('add_request.txt'))
        # self.assertEqual(output.get(), getData('delete_request.txt'))

    def testFourRequests(self):
        mngr = SolrConnectionManager(active=True)
        proc = SolrIndexProcessor(mngr)
        output = fakesolrconnection(
            mngr.getConnection(),
            schema=getData('schema.json'),
            fakedata=[
                # TODO: convert http response to solr api response
                getData('add_response.txt'),
                getData('delete_response.txt'),
                getData('commit_response.txt'),
            ],
        )
        proc.index(self.foo)
        proc.unindex(self.foo)
        proc.commit()
        mngr.closeConnection()
        self.assertEqual(len(output), 2)
        # self.failUnless(output.get().startswith(self.schema_request))
        self.assertEqual(output[0][0], 'schema')
        self.assertTrue(output[1].startswith('{"add": {"doc":'))
        self.assertEqual(output[1].count('{"add": {"doc":'), 1)
        self.assertEqual(output[1].count('"name": "python test doc"'), 1)
        self.assertEqual(output[1].count('"id": "500"'), 2)  # add + delete
        self.assertEqual(output[1].count('"delete": {"id": "500"}'), 1)
        self.assertTrue(output[1].endswith('"commit": {}}'))

    def testExtraRequest(self):
        # basically the same as `testThreeRequests`, except it
        # tests adding fake responses consecutively
        mngr = SolrConnectionManager(active=True)
        proc = SolrIndexProcessor(mngr)
        conn = mngr.getConnection()
        output = fakesolrconnection(conn, schema=getData('schema.json'))
        fakemore(conn, getData('add_response.txt'))
        proc.index(self.foo)
        fakemore(conn, getData('delete_response.txt'))
        proc.unindex(self.foo)
        # BBB: closeConnection don't flush queue ...
        mngr.closeConnection()
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0][0], 'schema')

        # self.assertEqual(len(output), 3)
        # self.failUnless(output.get().startswith(self.schema_request))
        # self.assertEqual(sortFields(output.get()),getData('add_request.txt'))
        # self.assertEqual(output.get(), getData('delete_request.txt'))


class ThreadedConnectionTests(TestCase):

    def testLocalConnections(self):
        provideUtility(SolrConnectionConfig(), ISolrConnectionConfig)
        mngr = SolrConnectionManager(active=True)
        proc = SolrIndexProcessor(mngr)
        mngr.setHost(active=True)
        schema = getData('schema.json')
        log = []

        def runner():
            fakesolrconnection(mngr.getConnection(), schema=schema)
            # read and cache the schema
            mngr.getSchema()
            response = getData('add_response.txt')
            # fake add response
            output = fakesolrconnection(mngr.getConnection(),
                                        fakedata=[response])
            # indexing sends data (???)
            proc.index(Foo(id='500', name='python test doc'))
            # commit sends data
            proc.commit()
            mngr.closeConnection()
            log.append(output)
            log.append(proc)
            log.append(mngr.getConnection())
        # after the runner was set up, another thread can be created and
        # started;  its output should contain the proper indexing request,
        # whereas the main thread's connection remain idle;  the latter
        # cannot be checked directly, but the connection object would raise
        # an exception if it was used to send a request without setting up
        # a fake response beforehand...
        thread = Thread(target=runner)
        thread.start()
        thread.join()
        conn = mngr.getConnection()             # get this thread's connection
        fakesolrconnection(conn, schema=schema)  # fake schema response
        mngr.getSchema()                        # read and cache the schema
        mngr.closeConnection()
        mngr.setHost(active=False)
        self.assertEqual(len(log), 3)
        # self.assertEqual(sortFields(log[0]), getData('add_request.txt'))
        self.assertEqual(log[0][0].count('"name": "python test doc"'), 1)
        self.assertEqual(log[0][0].count('"id": "500"'), 1)
        self.failUnless(isinstance(log[1], SolrIndexProcessor))
        self.failUnless(isinstance(log[2], SolrConnection))
        self.failUnless(isinstance(proc, SolrIndexProcessor))
        self.failUnless(isinstance(conn, SolrConnection))
        self.assertEqual(log[1], proc)      # processors should be the same...
        self.assertNotEqual(log[2], conn)   # but not the connections


def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)
