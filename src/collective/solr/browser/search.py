# -*- coding: utf-8 -*-
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.solr.browser.facets import SearchFacetsView


class SearchView(SearchFacetsView):

    index = ViewPageTemplateFile('search.pt')

    def __call__(self):
        return self.index()
