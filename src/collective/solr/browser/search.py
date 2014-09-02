# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.solr.browser.facets import SearchFacetsView

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
        b_start = 0
        b_size = 10
        catalog = getToolByName(self.context, 'portal_catalog')
        return json.dumps([
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
                b_size=b_size+1,
                hl='true'
            ) if brain is not None  # otherwise => AttributeError: 'NoneType'
        ])
