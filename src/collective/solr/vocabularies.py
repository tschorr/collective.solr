from Products.CMFCore.utils import getToolByName
from collective.solr.interfaces import ISolrConnectionConfig, \
    ISolrConnectionManager
from zope.app.component.hooks import getSite
from zope.component import queryUtility
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

class SolrIndexes(object):
    """ vocabulary provider yielding all available solr indexes """
    implements(IVocabularyFactory)

    def __call__(self, context):
        items = []
        manager = queryUtility(ISolrConnectionManager)
        if manager is not None:
            schema = manager.getSchema()
            if schema is not None:
                for name, info in sorted(schema.items()):
                    if 'indexed' in info and info.get('indexed', False):
                        items.append(name)
        if not items:
            config = queryUtility(ISolrConnectionConfig)
            if config is not None:
                items = config.filter_queries
        return SimpleVocabulary([SimpleTerm(item) for item in items])


class SolrScoreIndexes(object):
    """ vocabulary provider yielding all available score indexes (right now Field an ZCText)"""
    implements(IVocabularyFactory)

    def __call__(self, context):
        items = []
        context = getSite()        
        pc = getToolByName(context, 'portal_catalog')
        idxs = pc.getIndexObjects()
        for idx in idxs:
            if idx.meta_type in ['FieldIndex','ZCTextIndex']:
                items.append(SimpleTerm(idx.id, token=idx.id))
                
        return SimpleVocabulary(items)