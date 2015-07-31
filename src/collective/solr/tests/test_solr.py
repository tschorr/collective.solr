from unittest import TestCase
# from xml.etree.cElementTree import fromstring
from collective.solr.solr import SolrConnection
from collective.solr.tests.utils import getData
from collective.solr.tests.utils import fakesolrinterface


# TODO: use solr api mockup

class TestSolr(TestCase):

    def test_add(self):
        add_request = getData('add_request.txt')
        add_response = getData('add_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[add_response])
        c.add(id='500', name='python test doc')
        res = c.flush()
        self.assertEqual(res, None)  # TODO
        # self.assertEqual(len(res), 1)
        # res = res[0]
        self.failUnlessEqual(str(output), add_request)
        # Status
        # node = res.findall(".//int")[0]
        # self.failUnlessEqual(node.attrib['name'], 'status')
        # self.failUnlessEqual(node.text, '0')
        # QTime
        # node = res.findall(".//int")[1]
        # self.failUnlessEqual(node.attrib['name'], 'QTime')
        # self.failUnlessEqual(node.text, '4')
        # res.find('QTime')

    def test_add_with_boost_values(self):
        add_request = getData('add_request_with_boost_values.txt')
        add_response = getData('add_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[add_response])
        boost = {'': 2, 'id': 0.5, 'name': 5}
        c.add(boost_values=boost, id='500', name='python test doc')
        res = c.flush()
        self.assertEqual(res, None)  # TODO
        # self.assertEqual(len(res), 2)
        # res = res[0]
        self.failUnlessEqual(str(output), add_request)

    def test_commit(self):
        commit_request = getData('commit_request.txt')
        commit_response = getData('commit_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[commit_response])
        res = c.commit()
        self.assertEqual(res, None)  # TODO
        # self.assertEqual(len(res), 1)   # one request was sent
        # res = res[0]
        self.failUnlessEqual(str(output), commit_request)
        # Status
        # node = res.findall(".//int")[0]
        # self.failUnlessEqual(node.attrib['name'], 'status')
        # self.failUnlessEqual(node.text, '0')
        # QTime
        # node = res.findall(".//int")[1]
        # self.failUnlessEqual(node.attrib['name'], 'QTime')
        # self.failUnlessEqual(node.text, '55')
        # res.find('QTime')

    def test_optimize(self):
        commit_request = getData('optimize_request.txt')
        commit_response = getData('commit_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[commit_response])
        c.commit(optimize=True)
        self.failUnlessEqual(str(output), commit_request)

    def test_commit_no_wait_flush(self):
        commit_request = getData('commit_request.txt')
        commit_response = getData('commit_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[commit_response])
        c.commit(waitFlush=False)
        self.failUnlessEqual(str(output), commit_request)

    def test_commit_no_wait_searcher(self):
        commit_request = getData('commit_request_no_wait_searcher.txt')
        commit_response = getData('commit_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[commit_response])
        c.commit(waitSearcher=False)
        self.failUnlessEqual(str(output), commit_request)

    def test_commit_no_wait(self):
        commit_request = getData('commit_request_no_wait.txt')
        commit_response = getData('commit_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[commit_response])
        c.commit(waitFlush=False, waitSearcher=False)
        self.failUnlessEqual(str(output), commit_request)

    def test_search(self):
        # search_request = getData('search_request.txt')
        search_response = getData('search_response.json')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[search_response])
        res = c.search(
            q='+id:[* TO *]', fl='* score', wt='json', rows='10', indent='on')
        # res = fromstring(res.read())
        # normalize = lambda x: sorted(x.split('&'))      # sort request params
        # self.assertEqual(normalize(output.get()), normalize(search_request))
        self.assertEqual(
            output[0],
            ('search', ((), {'q': '+id:[* TO *]', 'indent': 'on', 'rows': '10',
                             'fl': '* score', 'wt': 'json'}))
        )
        # self.failUnless(res.find(('.//doc')))
        self.assertEqual(len(res.results()), 1)

    def test_delete(self):
        delete_request = getData('delete_request.txt')
        delete_response = getData('delete_response.txt')
        c = SolrConnection(host='localhost:8983', persistent=True)
        output = fakesolrinterface(c, fakedata=[delete_response])
        c.delete('500')
        res = c.flush()
        self.assertEqual(res, None)  # TODO
        # self.assertEqual(len(res), 2)   # two requests (delete + commit)
        # res = res[0]
        self.failUnlessEqual(str(output), delete_request)
        # Status
        # node = res.findall(".//int")[0]
        # self.failUnlessEqual(node.attrib['name'], 'status')
        # self.failUnlessEqual(node.text, '0')
        # QTime
        # node = res.findall(".//int")[1]
        # self.failUnlessEqual(node.attrib['name'], 'QTime')
        # self.failUnlessEqual(node.text, '0')
        # res.find('QTime')
