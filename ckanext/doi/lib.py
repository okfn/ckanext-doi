#!/usr/bin/env python
# encoding: utf-8
"""
Created by 'bens3' on 2013-06-21.
Copyright (c) 2013 'bens3'. All rights reserved.
"""

import os
import random
import datetime
import itertools
from logging import getLogger

from pylons import config
from requests.exceptions import HTTPError

from ckan.model import Session
import ckan.model as model
from ckan.lib import helpers as h
import ckan.plugins as p

from ckanext.doi.api import get_doi_api, get_prefix
from ckanext.doi.model.doi import DOI
from ckanext.doi.interfaces import IDoi
from ckanext.doi.exc import DOIMetadataException
from ckanext.doi.helpers import package_get_year

log = getLogger(__name__)


def _prepare_prefix(prefix):
    '''Ensure prefix has at least one '/' '''
    if prefix.count('/') == 0:
        prefix = prefix + '/'
    return prefix


def create_doi_from_identifier(package_id, identifier):
    '''Can be called when an identifier has already been created elsewhere.
    Does not ensure the identifier is unique'''
    doi = DOI(package_id=package_id, identifier=identifier)
    Session.add(doi)
    Session.commit()
    return doi


def create_unique_identifier(package_id, prefix):
    '''
    Create a unique identifier, using the prefix and a random number:
    10.5072/0044634

    Check the random number doesn't exist in the table or the datacite
    repository
    '''
    doi_api = get_doi_api()

    # validate prefix here prefix must be defined in the ini file, either
    # ckanext.doi.prefix and ckanext.doi.shoulder, or in
    # ckanext.doi.prefix_choices.

    # If prefix doesn't have at least one `/`, add one to the end
    prefix = _prepare_prefix(prefix)

    while True:
        # the api provider may have a make_identifier_id method, try it first,
        # then fall back to default.
        try:
            identifier_id = doi_api.make_identifier_id()
        except AttributeError:
            identifier_id = '{0:07}'.format(random.randint(1, 100000))

        # identifier = os.path.join(get_prefix(), identifier_id)
        identifier = prefix + identifier_id

        # Check this identifier doesn't exist in the table
        if not Session.query(DOI).filter(DOI.identifier == identifier).count():
            # And check against the api service
            try:
                doi = doi_api.get(identifier)
            except HTTPError:
                pass
            else:
                if doi.text:
                    continue

        doi = create_doi_from_identifier(package_id, identifier)

        return doi


def publish_doi(package_id, **kwargs):
    '''
    Publish a DOI to provider

    See MetadataDataCiteAPI.metadata_to_xml for param information
    @param package_id:
    @param kwargs contains metadata:
        @param title:
        @param creator:
        @param publisher:
        @param publisher_year:
    '''
    identifier = kwargs.get('identifier')

    doi_api = get_doi_api()

    # The ID of a dataset never changes, so use that for the URL
    url = os.path.join(get_site_url(), 'dataset', package_id)

    try:
        r = doi_api.create(url=url, **kwargs)
    except HTTPError as e:
        log.error('Publishing DOI for package {0} failed with error: {1}'
                  .format(package_id, e.message))
        raise e

    # If we have created the DOI, save it to the database
    if r.status_code == 201:
        # Update status for this package and identifier
        num_affected = Session.query(DOI) \
                            .filter_by(package_id=package_id,
                                       identifier=identifier) \
                            .update({"published": datetime.datetime.now()})
        # Raise an error if update has failed - should never happen unless
        # DataCite and local db get out of sync - in which case requires
        # investigating
        assert num_affected == 1, 'Updating local DOI failed'


def update_doi(package_id, **kwargs):
    '''Updates the DOI metadata'''
    doi = get_doi(package_id)
    kwargs['identifier'] = doi.identifier
    doi_api = get_doi_api()
    try:
        doi_api.update(**kwargs)
    except HTTPError as e:
        log.error('Could not update DOI for package {0}. ' +
                  'Failed with error: {1}'.format(package_id, e.message))
        raise e


def get_doi(package_id):
    '''Returns the local DOI object'''
    doi = Session.query(DOI).filter(DOI.package_id==package_id).first()
    return doi


def delete_doi(package_id):
    '''Delete the doi associated with a package_id'''
    doi = Session.query(DOI).filter(DOI.package_id==package_id).first()
    Session.delete(doi)
    Session.commit()


def get_site_url():
    '''
    Get the site URL
    Try and use ckanext.doi.site_url but if that's not set use ckan.site_url
    @return:
    '''
    site_url = config.get("ckanext.doi.site_url")

    if not site_url:
        site_url = config.get('ckan.site_url')

    return site_url.rstrip('/')


def build_metadata(pkg_dict, doi):
    # Build the datacite metadata - all of these are core CKAN fields which
    # should be the same across all CKAN sites This builds a dictionary keyed
    # by the datacite metadata xml schema
    metadata_dict = {
        'identifier': doi.identifier,
        'title': pkg_dict['title'],
        'creator': pkg_dict['author'],
        'publisher': config.get("ckanext.doi.publisher"),
        'publisher_year': package_get_year(pkg_dict),
        'description': pkg_dict['notes'],
    }

    # Convert the format to comma delimited
    try:
        # Filter out empty strings in the array (which is what we have if nothing is entered)
        # We want to make sure all None values are removed so we can compare
        # the dict here, with one loaded via action.package_show which doesn't
        # return empty values
        pkg_dict['res_format'] = filter(None, pkg_dict['res_format'])
        if pkg_dict['res_format']:
            metadata_dict['format'] = ', '.join([f for f in pkg_dict['res_format']])
    except KeyError:
        pass

    # If we have tag_string use that to build subject
    if 'tag_string' in pkg_dict:
        tags = pkg_dict.get('tag_string', '').split(',').sort()
        if tags:
            metadata_dict['subject'] = tags
    elif 'tags' in pkg_dict:
        # Otherwise use the tags list itself
        metadata_dict['subject'] = list(set([tag['name'] if isinstance(tag, dict) else tag for tag in pkg_dict['tags']])).sort()

    if pkg_dict.get('license_id', 'notspecified') != 'notspecified':

        licenses = model.Package.get_license_options()

        for license_title, license_id in licenses:
            if license_id == pkg_dict['license_id']:
                metadata_dict['rights'] = license_title
                break

    if pkg_dict.get('version', None):
        metadata_dict['version'] = pkg_dict['version']

    # Try and get spatial
    if 'extras_spatial' in pkg_dict and pkg_dict['extras_spatial']:
        geometry = h.json.loads(pkg_dict['extras_spatial'])

        if geometry['type'] == 'Point':
            metadata_dict['geo_point'] = '%s %s' % tuple(geometry['coordinates'])
        elif geometry['type'] == 'Polygon':
            # DataCite expects box coordinates, not geo pairs
            # So dedupe to get the box and join into a string
            metadata_dict['geo_box'] = ' '.join([str(coord) for coord in list(set(itertools.chain.from_iterable(geometry['coordinates'][0])))])

    # Allow plugins to alter the datacite DOI metadata
    # So other CKAN instances can add their own custom fields - and we can
    # Add our data custom to NHM
    for plugin in p.PluginImplementations(IDoi):
        plugin.build_metadata(pkg_dict, metadata_dict)

    return metadata_dict


def validate_metadata(metadata_dict):
    """
    Validate the metadata - loop through mandatory fields and check they are populated
    """

    # Check we have mandatory DOI fields
    mandatory_fields = ['title', 'creator']

    # Make sure our mandatory fields are populated
    for field in mandatory_fields:
        if not metadata_dict.get(field, None):
            raise DOIMetadataException('Missing DataCite required field %s' % field)
