from Products.Five import BrowserView
from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.utils import explainResults
from zope.component import queryUtility

class SearchExplainView(BrowserView):
    """ view for displaying Solr debug explain """
    
    def __call__(self, response, uid):
        explanations = explainResults(response)
        if explanations:
            return explanations.get(uid, None)
        else:
            return None