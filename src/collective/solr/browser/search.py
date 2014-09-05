# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.solr.browser.facets import SearchFacetsView
from collective.solr.dispatcher import solrSearchResults

import json


class SearchView(SearchFacetsView):

    index = ViewPageTemplateFile('search.pt')

    def __call__(self):
        b_start = 0
        b_size = 30
        catalog = getToolByName(self.context, 'portal_catalog')
        self.results = catalog(
            REQUEST=self.request,
            use_types_blacklist=True,
            use_navigation_root=True,
            b_start=b_start,
            b_size=b_size+1,
            hl='true'
        )
        return self.index()


class JSONSearchResults(SearchFacetsView):

    def __call__(self):
        b_start = self.request.get('b_start', 1)
        b_size = self.request.get('b_size', 10)
        catalog = getToolByName(self.context, 'portal_catalog')
        results = [
            {
                'title': brain.Title,
                'id': brain.id,
                'portal_type': brain.portal_type,
                'url': brain.getURL()
            }
            for brain in catalog(
                REQUEST=self.request,
                use_types_blacklist=True,
                use_navigation_root=True,
                b_start=b_start,
                b_size=b_size,
                hl='true'
            ) if brain is not None  # otherwise => AttributeError: 'NoneType'
        ]
        SearchableText = self.request.get('SearchableText')
        solr_search_results = solrSearchResults(
            SearchableText=SearchableText,
            facet='true',
            facet_field='portal_type'
        )
        current_facet_value = self.request['fq'].split(':')[1]
        facets = solr_search_results.facet_counts['facet_fields']['portal_type']
        return json.dumps({
            'results': results,
            'facets': facets,
            'totalItems': facets[current_facet_value],
        })
