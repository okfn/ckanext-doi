#!/usr/bin/env python
# encoding: utf-8
"""
Created by 'bens3' on 2013-06-21.
Copyright (c) 2013 'bens3'. All rights reserved.
"""

import os
import abc
from logging import getLogger

import requests
from pylons import config

import ckanext.doi.api
from ckanext.doi.api.mixins import MetadataToDataCiteXmlMixin

log = getLogger(__name__)


ENDPOINT = 'https://mds.datacite.org'
TEST_ENDPOINT = 'https://test.datacite.org/mds'


def get_endpoint():
    """
    Get the EZID endpoint
    @return: test endpoint if we're in test mode
    """
    return TEST_ENDPOINT if ckanext.doi.api.get_test_mode() else ENDPOINT


class DataCiteAPI(object):

    @abc.abstractproperty
    def path(self):
        return None

    def _call(self, **kwargs):

        account_name = config.get("ckanext.doi.account_name")
        account_password = config.get("ckanext.doi.account_password")
        endpoint = os.path.join(get_endpoint(), self.path)

        try:
            path_extra = kwargs.pop('path_extra')
        except KeyError:
            pass
        else:
            endpoint = os.path.join(endpoint, path_extra)

        try:
            method = kwargs.pop('method')
        except KeyError:
            method = 'get'

        # Add authorisation to request
        kwargs['auth'] = (account_name, account_password)

        log.info("Calling %s:%s - %s", endpoint, method, kwargs)

        r = getattr(requests, method)(endpoint, **kwargs)
        r.raise_for_status()
        # Return the result
        return r


class MetadataDataCiteAPI(DataCiteAPI, MetadataToDataCiteXmlMixin):
    """
    Calls to DataCite metadata API
    """
    path = 'metadata'

    def get(self, doi):
        """
        URI: https://datacite.org/mds/metadata/{doi} where {doi} is a specific DOI.
        @param doi:
        @return: The most recent version of metadata associated with a given DOI.
        """
        return self._call(path_extra=doi)

    def upsert(self, identifier, title, creator, publisher, publisher_year, **kwargs):
        """
        URI: https://test.datacite.org/mds/metadata
        This request stores new version of metadata. The request body must contain valid XML.
        @param metadata_dict: dict to convert to xml
        @return: URL of the newly stored metadata
        """
        xml = self.metadata_to_xml(identifier, title, creator, publisher, publisher_year, **kwargs)
        r = self._call(method='post', data=xml, headers={'Content-Type': 'application/xml'})
        assert r.status_code == 201, 'Operation failed ERROR CODE: %s' % r.status_code
        return r

    def delete(self, doi):
        """
        URI: https://test.datacite.org/mds/metadata/{doi} where {doi} is a specific DOI.
        This request marks a dataset as 'inactive'.
        @param doi: DOI
        @return: Response code
        """
        return self._call(path_extra=doi, method='delete')


class DOIDataCiteAPI(DataCiteAPI):
    """
    Calls to DataCite DOI API
    """
    path = 'doi'

    def get(self, doi):
        """
        Get a specific DOI
        URI: https://datacite.org/mds/doi/{doi} where {doi} is a specific DOI.

        @param doi: DOI
        @return: This request returns an URL associated with a given DOI.
        """
        r = self._call(path_extra=doi)
        return r

    def list(self):
        """
        list all DOIs
        URI: https://datacite.org/mds/doi

        @return: This request returns a list of all DOIs for the requesting data centre. There is no guaranteed order.
        """
        return self._call()

    def upsert(self, doi, url):
        """
        URI: https://datacite.org/mds/doi
        POST will mint new DOI if specified DOI doesn't exist. This method will attempt to update URL if you specify existing DOI. Standard domains and quota restrictions check will be performed. A Datacentre's doiQuotaUsed will be increased by 1. A new record in Datasets will be created.

        @param doi: doi to mint
        @param url: url doi points to
        @return:
        """
        return self._call(
            # Send as data rather than params so it's posted as x-www-form-urlencoded
            data={
                'doi': doi,
                'url': url
            },
            method='post',
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

class MediaDataCiteAPI(DataCiteAPI):
    """
    Calls to DataCite Metadata API
    """
    pass

