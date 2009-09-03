# -*- coding: utf-8 -*-

from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.manager import SolrConnectionConfig
from collective.solr.score import buildScoreQuery, ScoreFactory
from unittest import TestCase, defaultTestLoader, main
from zope.component import provideUtility

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
        
def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)

if __name__ == '__main__':
    main(defaultTest='test_suite')
