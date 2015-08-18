import os
import abc
import random
import logging

import requests
from pylons import config

import ckanext.doi.api


log = logging.getLogger(__name__)

ENDPOINT = 'https://ezid.cdlib.org'


class EzidAPI(object):

    @abc.abstractproperty
    def path(self):
        return None

    def _call(self, **kwargs):

        account_name = config.get("ckanext.doi.account_name")
        account_password = config.get("ckanext.doi.account_password")
        endpoint = os.path.join(ENDPOINT, self.path)

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

    def make_identifier_id(self):
        '''Make an identifier in the form 'FK20000000' '''
        prefix = 'FK2' if ckanext.doi.api.get_test_mode() else ''
        return '{1}{0:07}'.format(random.randint(1, 100000), prefix)


class DOIEzidAPI(EzidAPI):
    """
    Calls to EZID DOI API
    """
    path = 'id'

    def get(self, doi):
        """
        Get a specific DOI
        URI: http://ezid.cdlib.org/id/doi:{doi} where {doi} is a specific DOI.

        @param doi: DOI
        @return: This request returns an URL associated with a given DOI.
        """
        r = self._call(path_extra='doi:{0}'.format(doi))
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
