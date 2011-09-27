from string import maketrans
from re import compile, UNICODE

from Acquisition import aq_base
from unidecode import unidecode
from zope.component import queryUtility

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
        data['allowedRolesAndUsers'] = [r.replace(':', '$') for r in allowed]
    language = data.get('Language', None)
    if language is not None:
        if language == '':
            data['Language'] = 'any'
        elif isinstance(language, (tuple, list)) and '' in language:
            data['Language'] = [lang or 'any' for lang in language]
    searchable = data.get('SearchableText', None)
    if searchable is not None:
        if isSimpleTerm(searchable):        # use prefix/wildcard search
            searchable = '(%s* OR %s)' % (
                prepare_wildcard(searchable), searchable)
        if isinstance(searchable, unicode):
            searchable = searchable.encode('utf-8')
        data['SearchableText'] = searchable.translate(translation_map)


simpleTerm = compile(r'^[\w\d]+$', UNICODE)
def isSimpleTerm(term):
    if isinstance(term, str):
        try:
            term = unicode(term, 'utf-8')
        except UnicodeDecodeError:
            pass
    return bool(simpleTerm.match(term.strip()))


def prepare_wildcard(value):
    # wildcards prevent Solr's field analyzer to run. So we need to replicate
    # all logic that's usually done in the text field.
    # Unfortunately we cannot easily inspect the field analyzer and tokenizer,
    # so we assume the default config contains ICUFoldingFilterFactory and hope
    # unidecode will produce the same results
    if not isinstance(value, unicode):
        value = unicode(value, 'utf-8', 'ignore')
    return str(unidecode(value).lower())


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


def padResults(results, start=0, **kw):
    if start:
        results[0:0] = [None] * start
    found = int(results.numFound)
    tail = found - len(results)
    results.extend([None] * tail)
