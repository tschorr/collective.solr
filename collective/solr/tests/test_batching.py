
from socket import error
from socket import timeout
from time import sleep
from unittest import defaultTestLoader

from collective.indexing.interfaces import IIndexQueueProcessor
from collective.solr.batched import BatchedResults
from collective.solr.exceptions import SolrInactiveException
from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.interfaces import ISolrConnectionManager
from collective.solr.interfaces import ISolrIndexQueueProcessor
from collective.solr.interfaces import ISearch
from collective.solr.tests.base import SolrTestCase
from collective.solr.tests.utils import fakehttp
from collective.solr.tests.utils import fakeServer
from collective.solr.tests.utils import getData
from collective.solr.tests.utils import numFound
from collective.solr.utils import activate
from transaction import commit
from zope.component import getUtilitiesFor
from zope.component import queryUtility


class BatchedTests(SolrTestCase):

    def afterSetUp(self):
        activate()
        manager = queryUtility(ISolrConnectionManager)
        self.connection = connection = manager.getConnection()
        connection.deleteByQuery('[* TO *]')
        connection.commit()
        result = connection.search(q='[* TO *]').read()
        self.assertEqual(numFound(result), 0)
        # ignore any generated logging output
        self.portal.REQUEST.RESPONSE.write = lambda x: x

        config = queryUtility(ISolrConnectionConfig)
        self.batch_size = config.batch_size = 5

    def beforeTearDown(self):
        activate(active=False)
        commit()

    def testIteration(self):
        for i in range(10):
            self.folder.invokeFactory('Document', id='doc%i' % i,
                    title='Document %i' % i)
        commit()
        catalog = self.portal.portal_catalog
        results = catalog(SearchableText='Document')
        self.assert_(isinstance(results, BatchedResults),
                'not getting BatchedResults')
        length = len(results)
        count = 0
        for flare in results:
            count += 1
        self.assertEqual(length, count)
        self.folder.manage_delObjects(['doc%i' % i for i in range(10)])
        commit()

    def testSlice(self):
        for i in range(10):
            self.folder.invokeFactory('Document', id='doc%i' % i,
                    title='Document %i' % i)
        commit()
        catalog = self.portal.portal_catalog
        results = catalog(SearchableText='Document')
        self.assert_(isinstance(results, BatchedResults),
                'not getting BatchedResults')
        length = len(results)
        start = 2
        stop = 8
        sliced = results[start:stop]
        slice_length = len(sliced)
        self.assertNotEqual(length, slice_length)
        self.assertEqual(slice_length, stop-start)
        t1 = [x for x in sliced]
        t2 = list()
        for i in range(start, stop):
            t2.append(results[i])
        self.assertEqual(t1, t2)
        sliced = results[:stop]
        t1 = [x for x in sliced]
        t2 = list()
        for i in range(stop):
            t2.append(results[i])
        self.assertEqual(t1, t2)
        sliced = results[start:]
        t1 = [x for x in sliced]
        t2 = list()
        for i in range(start, length):
            t2.append(results[i])
        self.assertEqual(t1, t2)
        self.folder.manage_delObjects(['doc%i' % i for i in range(10)])
        commit()

    def testNegativeIndex(self):
        for i in range(10):
            self.folder.invokeFactory('Document', id='doc%i' % i,
                    title='Document %i' % i)
        commit()
        catalog = self.portal.portal_catalog
        results = catalog(SearchableText='Document')
        self.assert_(isinstance(results, BatchedResults),
                'not getting BatchedResults')
        res = results[-1]
        length = len(results)
        res2 = results[length - 1]
        self.assertEquals(res, res2)
        sliced = results[-5:-2]
        sliced2 = results[length-5:length-2]
        s1 = [x for x in sliced]
        s2 = [x for x in sliced2]
        self.assertEqual(s1, s2)
        self.folder.manage_delObjects(['doc%i' % i for i in range(10)])
        commit()

    def testLimit(self):
        for i in range(10):
            self.folder.invokeFactory('Document', id='doc%i' % i,
                    title='Document %i' % i)
        commit()
        catalog = self.portal.portal_catalog
        results = catalog(SearchableText='Document', sort_limit=4)
        self.assert_(isinstance(results, BatchedResults),
                'not getting BatchedResults')
        self.assertEqual(len(results), 4)
        count = 0
        for x in results:
            count += 1
        self.assertEqual(count, 4)
        self.folder.manage_delObjects(['doc%i' % i for i in range(10)])
        commit()

    def testBatching(self):
        batch_size = self.batch_size
        for i in range(10):
            self.folder.invokeFactory('Document', id='doc%i' % i,
                    title='Document %i' % i)
        commit()
        catalog = self.portal.portal_catalog
        results = catalog(SearchableText='Document')
        self.assert_(isinstance(results, BatchedResults),
                'not getting BatchedResults')
        self.assertEqual(len(results._results), batch_size)
        self.assert_(len(results) > batch_size)
        res = results[0]
        self.assertEqual(res, results._results[0])
        res2 = results[batch_size] # should trigger a new batch
        self.assertNotEqual(res, res2)
        self.assertEqual(res2, results._results[0])
        self.folder.manage_delObjects(['doc%i' % i for i in range(10)])
        commit()

    def testIndexError(self):
        batch_size = self.batch_size
        for i in range(10):
            self.folder.invokeFactory('Document', id='doc%i' % i,
                    title='Document %i' % i)
        commit()
        catalog = self.portal.portal_catalog
        results = catalog(SearchableText='Document')
        self.assert_(isinstance(results, BatchedResults),
                'not getting BatchedResults')
        self.assertRaises(IndexError, results.__getitem__, len(results))
        self.folder.manage_delObjects(['doc%i' % i for i in range(10)])
        commit()

    def testEmptySearch(self):
        batch_size = self.batch_size
        catalog = self.portal.portal_catalog
        results = catalog(SearchableText='jfakjweifjskdfjuiwehf')
        self.assert_(isinstance(results, BatchedResults),
                'not getting BatchedResults')
        self.assertEqual(len(results), 0)
        self.assertRaises(IndexError, results.__getitem__, 0)
        self.assertRaises(IndexError, results.__getitem__, -1)
        sliced = results[:10]
        self.assertEqual(len(sliced), 0)
        self.assertRaises(IndexError, sliced.__getitem__, 0)
        self.assertRaises(IndexError, sliced.__getitem__, -1)

def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)

