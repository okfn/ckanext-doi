import re
import os
import abc
import random
import logging

import requests
from pylons import config

import ckanext.doi.api
from ckanext.doi.api.mixins import MetadataToDataCiteXmlMixin


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

        r = getattr(requests, method)(endpoint, **kwargs)
        r.raise_for_status()
        # Return the result
        return r

    def make_identifier_id(self):
        '''Make an identifier in the form 'FK20000000' '''
        prefix = 'FK2' if ckanext.doi.api.get_test_mode() else ''
        return '{1}{0:07}'.format(random.randint(1, 100000), prefix)


class DOIEzidAPI(EzidAPI, MetadataToDataCiteXmlMixin):
    '''
    Calls to EZID DOI API
    '''
    path = 'id'

    def get(self, doi):
        '''
        Get a specific DOI
        URI: http://ezid.cdlib.org/id/doi:{doi} where {doi} is a specific DOI.

        @param doi: DOI
        @return: This request returns an URL associated with a given DOI.
        '''
        return self._call(path_extra='doi:{0}'.format(doi))

    # def list(self):
    #     '''
    #     list all DOIs
    #     URI: https://datacite.org/mds/doi

    #     @return: This request returns a list of all DOIs for the requesting data centre. There is no guaranteed order.
    #     '''
    #     return self._call()

    # def upsert(self, doi, url):
    #     '''
    #     URI: https://datacite.org/mds/doi

    #     POST will mint new DOI if specified DOI doesn't exist. This method
    #     will attempt to update URL if you specify existing DOI. Standard
    #     domains and quota restrictions check will be performed. A
    #     Datacentre's doiQuotaUsed will be increased by 1. A new record in
    #     Datasets will be created.

    #     @param doi: doi to mint
    #     @param url: url doi points to
    #     @return:
    #     '''
    #     return self._call(
    #         # Send as data rather than params so it's posted as x-www-form-urlencoded
    #         data={
    #             'doi': doi,
    #             'url': url
    #         },
    #         method='post',
    #         headers={'Content-Type': 'application/x-www-form-urlencoded'}
    #     )

    def _create_or_update(self, method, identifier, title, creator, publisher,
                          publisher_year, url=None, **kwargs):
        '''
        URI: https://ezid.cdlib.org/id/doi:{identifier}

        This request stores new version of metadata. The request body must
        contain valid XML. This method is the same for creating or updating,
        as determined by the http method used (put for create, post for
        update).

        From: http://ezid.cdlib.org/doc/apidoc.html

            Care must be taken to escape structural characters that appear in
            element names and values, specifically, line terminators (both
            newlines ("\n", U+000A) and carriage returns ("\r", U+000D)) and,
            in element names, colons (":", U+003A). EZID employs percent-
            encoding as the escaping mechanism, and thus percent signs ("%",
            U+0025) must be escaped as well.
        '''
        def escape(s):
            return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), s)

        metadata_xml = self.metadata_to_xml(identifier, title, creator,
                                            publisher, publisher_year,
                                            **kwargs)

        data = {
            'datacite': metadata_xml,
        }
        if url is not None:
            data.update({'_target': url})

        # data in anvl format requires escaping
        anvl = "\n".join("%s: %s" % (escape(name), escape(value))
                         for name, value in data.items()).encode("UTF-8")

        r = self._call(path_extra='doi:{0}'.format(identifier), method=method,
                       data=anvl, headers={'Content-Type': 'text/plain'})
        return r

    def create(self, url, identifier, title, creator, publisher,
               publisher_year, **kwargs):
        '''
        Create a metadata entry on EZID.
        '''
        return self._create_or_update('put', identifier, title, creator,
                                      publisher, publisher_year, url, **kwargs)

    def update(self, identifier, title, creator, publisher, publisher_year,
               **kwargs):
        '''
        Update an existing entry on EZID.
        '''
        return self._create_or_update('post', identifier, title, creator,
                                      publisher, publisher_year, **kwargs)

    def delete(self, doi):
        '''
        URI: https://test.datacite.org/mds/metadata/{doi} where {doi} is a specific DOI.
        This request marks a dataset as 'inactive'.
        @param doi: DOI
        @return: Response code
        '''
        return self._call(path_extra=doi, method='delete')
