from zope.interface import Interface
from plone.indexer import indexer


def path_string(obj, **kwargs):
    """ return physical path as a string """
    return '/'.join(obj.getPhysicalPath())


def path_depth(obj, **kwargs):
    """ return depth of physical path """
    return len(obj.getPhysicalPath())


def path_parents(obj, **kwargs):
    """ return all parent paths leading up to the object """
    elements = obj.getPhysicalPath()
    return ['/'.join(elements[:n+1]) for n in xrange(1, len(elements))]


# the `indexer` decorator needs to be applied manually here, since plone
# versions before 3.3 need to be able to access the bare indexing functions
path_string_indexer = indexer(Interface)(path_string)
path_depth_indexer = indexer(Interface)(path_depth)
path_parents_indexer = indexer(Interface)(path_parents)


def registerAttributes():
    try:
        from Products.CMFPlone.CatalogTool import registerIndexableAttribute
        registerIndexableAttribute('path_string', path_string)
        registerIndexableAttribute('path_depth', path_depth)
        registerIndexableAttribute('path_parents', path_parents)
    except ImportError:
        pass
