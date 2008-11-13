from zope.interface import implements
from zope.component import queryUtility, queryMultiAdapter, getSiteManager
from zope.publisher.interfaces.http import IHTTPRequest
from Products.ZCatalog.ZCatalog import ZCatalog

from collective.solr.interfaces import ISolrConnectionConfig
from collective.solr.interfaces import ISearchDispatcher
from collective.solr.interfaces import ISearch
from collective.solr.interfaces import IFlare
from collective.solr.utils import isActive, prepareData
from collective.solr.mangler import mangleQuery
from collective.solr.mangler import extractQueryParameters
from collective.solr.mangler import cleanupQueryParameters

from collective.solr.monkey import patchCatalogTool
patchCatalogTool()      # patch catalog tool to use the dispatcher...

from collective.solr.attributes import registerAttributes
registerAttributes()    # register additional indexable attributes


class FallBackException(Exception):
    """ exception indicating the dispatcher should fall back to searching
        the portal catalog """


class SearchDispatcher(object):
    """ adapter for potentially dispatching a given query to an
        alternative search backend (instead of the portal catalog) """
    implements(ISearchDispatcher)

    def __init__(self, context):
        self.context = context

    def __call__(self, request, **keywords):
        """ decide on a search backend and perform the given query """
        if isActive():
            try:
                return solrSearchResults(request, **keywords)
            except FallBackException:
                pass
        return ZCatalog.searchResults(self.context, request, **keywords)


class BatchedResults(object):

    def __init__(self, search, query, batch_size, request, offset=0,
            end=None, **params):
        self._search = search
        self._query = query
        self._batch_size = batch_size
        self._params = params.copy()
        if 'rows' in params:
            self._limit = limit = params['rows']
        else:
            self._limit = limit = None
        if limit is not None and  limit < batch_size:
            self._batch_size = limit
        self._request = request
        self._total = None
        self._offset = offset
        self._end = end
        # do first search
        self._doSearch()

    def __len__(self):
        if self._total is None:
            self._doSearch()
        return self._total

    def __getitem__(self, index):
        length = len(self)
        if isinstance(index, slice):
            params = self._params.copy()
            start = index.start
            if start is None:
                start = 0
            if start < 0:
                start = length + start
            end = index.stop
            if end is None:
                end = length
            elif end < 0:
                end = length + end
            if end < start:
                return list()
            return BatchedResults(self._search, self._query, self._batch_size,
                    self._request, offset=start, end=end, **params)
        if index < 0:
            index = length + index
        if index >= length or length == 0:
            raise IndexError('list index out of range')
        index = index + self._offset
        end = self._start + self._batch_size - 1
        if index < self._start or index > end:
            self._doSearch(index=index)
        index = index - self._start
        return self._results[index]

    def _wrap(self, flare):
        adapter = queryMultiAdapter((flare, self._request), IFlare)
        return adapter is not None and adapter or flare

    def __iter__(self):
        wrap = self._wrap
        if self._start:
            self._doSearch()
        index = 0
        while index < len(self):
            yield self[index]
            index += 1

    def _doSearch(self, index=None):
        search = self._search
        query = self._query
        params = self._params.copy()
        start = 0
        size = self._batch_size
        limit = self._limit
        if index is not None:
            start = (index / size) * size
        self._start = start = params['start'] = start + self._offset
        params['rows'] = size
        end = start + size - 1
        if self._end and end > self._end:
            # if we've been sliced don't get results that won't be in the slice
            params['rows'] = self._end - start + 1
            end = self._end
        if limit is not None:
            if end >= limit:
                # if the query included a limit make sure we don't go over the
                # limit
                params['rows'] = limit - start
        results = search(query, fl='* score', **params)
        wrap = self._wrap
        self._results = map(wrap, results)
        if self._total is None:
            total = int(results.numFound)
            if limit is not None and self._end is not None:
                # if we've been sliced and there is a limit the results count
                # is the smallest of total number of results, the limit or
                # the slice size
                self._total = min(total, limit, (self._end - self._offset))
            elif self._end is not None:
                # if we've been sliced and there is no limit the results count
                # is the smallest of total number of results or the slice size
                self._total = min(total, (self._end - self._offset))
            elif limit is not None:
                # limit but no slice, results count is smallest of limit or
                # total number of results
                self._total = min(total, limit)
            else:
                self._total = total


def solrSearchResults(request=None, **keywords):
    """ perform a query using solr after translating the passed in
        parameters with portal catalog semantics """
    search = queryUtility(ISearch)
    config = queryUtility(ISolrConnectionConfig)
    if request is None:
        # try to get a request instance, so that flares can be adapted to
        # ploneflares and urls can be converted into absolute ones etc;
        # however, in this case any arguments from the request are ignored
        request = getattr(getSiteManager(), 'REQUEST', None)
        args = keywords
    elif IHTTPRequest.providedBy(request):
        args = request.form.copy()  # ignore headers and other stuff
        args.update(keywords)       # keywords take precedence
    else:
        assert isinstance(request, dict), request
        args = request.copy()
        args.update(keywords)       # keywords take precedence
    if config.required:
        required = set(config.required).intersection(args)
        if required:
            for key in required:
                if not args[key]:
                    raise FallBackException
        else:
            raise FallBackException
    mangleQuery(args)
    prepareData(args)
    query = search.buildQuery(**args)
    schema = search.getManager().getSchema() or {}
    params = cleanupQueryParameters(extractQueryParameters(args), schema)
    return BatchedResults(search, query, config.batch_size, request,
            **params)
    #results = search(query, fl='* score', **params)
    #def wrap(flare):
    #    """ wrap a flare object with a helper class """
    #    adapter = queryMultiAdapter((flare, request), IFlare)
    #    return adapter is not None and adapter or flare
    #return map(wrap, results)

