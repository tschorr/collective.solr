import logging
from zope.interface import implements
from zope.component import queryUtility
from Missing import MV

from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.interfaces import ISolrConnectionManager
from collective.solr.interfaces import IKeywords
from collective.solr.parser import SolrResponse
from collective.solr.exceptions import SolrInactiveException
from collective.solr.queryparser import quote

logger = logging.getLogger('collective.solr.search')
#hdlr = logging.FileHandler('var/log/collective.solr.log')
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#hdlr.setFormatter(formatter)
#logger.addHandler(hdlr)
#logger.setLevel(logging.DEBUG)

class Keywords(object):
    """ a search utility for solr """
    implements(IKeywords)

    def __init__(self):
        self.manager = None

    def getManager(self):
        if self.manager is None:
            self.manager = queryUtility(ISolrConnectionManager)
        return self.manager

    def search(self, name, **parameters):
        """ perform a search with the given querystring and parameters """
        manager = self.getManager()
        manager.setSearchTimeout()
        connection = manager.getConnection()
        if connection is None:
            raise SolrInactiveException
        if not 'rows' in parameters:
            config = queryUtility(ISolrConnectionConfig)
            parameters['rows'] = config.max_results or ''
        logger.debug('looking up keywords for %r (%r)', name, parameters)
        if 'sort' in parameters:    # issue warning for unknown sort indices
            index, order = parameters['sort'].split()
            schema = manager.getSchema() or {}
            field = schema.get(index, None)
            if field is None or not field.stored:
                logger.warning('sorting on non-stored attribute "%s"', index)
        response = connection.uniqueValuesFor(name, **parameters)
        results = SolrResponse(response)
        keywords=[keyword for keyword in results.terms[name]]
        response.close()
        manager.setTimeout(None)
        return keywords

    __call__ = search

