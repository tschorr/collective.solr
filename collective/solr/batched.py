
from collective.solr.interfaces import IFlare
from zope.component import queryMultiAdapter




class BatchedResults(object):

    __allow_access_to_unprotected_subobjects__ = 1

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
        self._response = response = search(query, fl='* score', **params)
        results = response.results()
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


    def __getattr__(self, name):
        response = self._response
        if not hasattr(response, name):
            raise AttributeError, name
        return getattr(response, name)


