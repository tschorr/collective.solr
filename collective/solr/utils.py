from zope.component import queryUtility
from Acquisition import aq_base
from string import maketrans

from collective.solr.interfaces import ISolrConnectionConfig


def isActive():
    """ indicate if the solr connection should/can be used """
    config = queryUtility(ISolrConnectionConfig)
    if config is not None:
        return config.active
    return False


def activate(active=True):
    """ (de)activate the solr integration """
    config = queryUtility(ISolrConnectionConfig)
    config.active = active


def setupTranslationMap():
    """ prepare translation map to remove all control characters except
        tab, new-line and carriage-return """
    ctrls = trans = ''
    for n in range(0, 32):
        char = chr(n)
        ctrls += char
        if char in '\t\n\r':
            trans += char
        else:
            trans += ' '
    return maketrans(ctrls, trans)

translation_map = setupTranslationMap()


def prepareData(data):
    """ modify data according to solr specifics, i.e. replace ':' by '$'
        for "allowedRolesAndUsers" etc """
    allowed = data.get('allowedRolesAndUsers', None)
    if allowed is not None:
        if type(allowed) in (dict,):
            allowed['query'] = [x.replace(':','$') for x in allowed['query']]
        else:
            data['allowedRolesAndUsers'] = [x.replace(':','$') for x in allowed]
    searchable = data.get('SearchableText', None)
    if searchable is not None:
        if isinstance(searchable, unicode):
            searchable = searchable.encode('utf-8')
        data['SearchableText'] = searchable.translate(translation_map)


def findObjects(origin):
    """ generator to recursively find and yield all zope objects below
        the given start point """
    traverse = origin.unrestrictedTraverse
    base = '/'.join(origin.getPhysicalPath())
    cut = len(base) + 1
    paths = [base]
    for idx, path in enumerate(paths):
        obj = traverse(path)
        yield path[cut:], obj
        if hasattr(aq_base(obj), 'objectIds'):
            for id in obj.objectIds():
                paths.insert(idx + 1, path + '/' + id)
