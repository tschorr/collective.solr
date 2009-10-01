from zope.interface import implements
from collective.solr.interfaces import ISolrScore, ISolrConnectionConfig
from zope.component import queryUtility

class ScoreFactory(object):
    """ Simple score factory """
    implements(ISolrScore)
    
    @property
    def query(self):
        if not self.value:
            return '%(search)s'
        else:
            return str(self.value)

    def asTuple(self):
        return (self.idx, self.query, self.score)
            

def buildScoreQuery(query):
    """ build score query method """
    template = "%s:%s^%s"
    config = queryUtility(ISolrConnectionConfig)
    searchstring = query.get('SearchableText')
    if searchstring: 
        searchstring = str(searchstring.split(':')[-1])
    for score in config.scores:
        if not score.value and not searchstring:
            continue
        if score.idx in query:
            query[score.idx] += ' %s' % template % score.asTuple() % {'search': searchstring} 
        else:
            query[score.idx] = template % score.asTuple() % {'search': searchstring} 
    return query