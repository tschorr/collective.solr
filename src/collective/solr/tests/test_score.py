# -*- coding: utf-8 -*-

from collective.solr.interfaces import ISolrConnectionConfig,\
    ISolrConnectionManager, ISearch
from collective.solr.manager import SolrConnectionConfig
from collective.solr.score import buildScoreQuery, ScoreFactory
from collective.solr.tests.base import SolrTestCase
from collective.solr.utils import explainResults

from unittest import TestCase, defaultTestLoader, main
from zope.component import provideUtility, queryUtility
from transaction import commit

def addScore(idx,value,score):
    _score = ScoreFactory()
    _score.idx = idx
    _score.value = value
    _score.score = score
    return _score

class ScoreTests(TestCase):

    def setUp(self):
        self.config = SolrConnectionConfig()
        provideUtility(self.config, ISolrConnectionConfig)
                
    def testBasicScore(self):
        self.assertEqual(buildScoreQuery({'SearchableText': 'foobar'}), {'SearchableText': 'foobar'})
        
        self.config.scores.append(addScore('portal_type','Folder',10.0))
        self.assertEqual(buildScoreQuery({'SearchableText': 'foobar'})['portal_type'], 'portal_type:Folder^10.0')
        self.assertEqual(buildScoreQuery({})['portal_type'], 'portal_type:Folder^10.0')
                
        self.config.scores.append(addScore('review_state','published',1.0))
        self.assertEqual(buildScoreQuery({})['portal_type'], 'portal_type:Folder^10.0')
        self.assertEqual(buildScoreQuery({})['review_state'], 'review_state:published^1.0')
        
        self.config.scores.append(addScore('Description',None,50.0))
        self.assertEqual(buildScoreQuery({}).get('Description'),None)
        self.assertEqual(buildScoreQuery({'SearchableText': 'foobar'})['Description'], 'Description:foobar^50.0')
        
class ScoreExplanationTests(SolrTestCase):

    def beforeTearDown(self):
        # resetting the solr configuration after each test isn't strictly
        # needed at the moment, but it triggers the `ConnectionStateError`
        # when the other tests (in `errors.txt`) is trying to perform an
        # actual solr search...
        queryUtility(ISolrConnectionManager).setHost(active=False)
                
    def testBasicExplanation(self):
        config = queryUtility(ISolrConnectionConfig)
        search = queryUtility(ISearch)        

        config.active = True
        self.assertEqual(explainResults(search('test')), None)        
        config.debug_query = True
        self.assertNotEqual(explainResults(search('test')), None)
        
    def testExplanationInfo(self):
        self.setRoles(['Manager'])
        config = queryUtility(ISolrConnectionConfig)
        search = queryUtility(ISearch)
     
        config.active = True
        self.portal.invokeFactory('Document','doc1')
        self.portal.doc1.setText('Lorem')
        commit()
        
        config.debug_query = True
        self.assertNotEqual(explainResults(search('Lorem')).get(self.portal.doc1.UID()), None)

def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)

if __name__ == '__main__':
    main(defaultTest='test_suite')
