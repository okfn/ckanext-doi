#!/usr/bin/env python
# encoding: utf-8
"""
Created by 'bens3' on 2013-06-21.
Copyright (c) 2013 'bens3'. All rights reserved.
"""

from pylons import config
from datetime import datetime
import dateutil.parser as parser

import ckan.plugins.toolkit as toolkit
import ckan.authz as authz

import logging
log = logging.getLogger(__name__)


def package_get_year(pkg_dict):
    """
    Helper function to return the package year published
    @param pkg_dict:
    @return:
    """
    if not isinstance(pkg_dict['metadata_created'], datetime):
        pkg_dict['metadata_created'] = \
            parser.parse(pkg_dict['metadata_created'])

    return pkg_dict['metadata_created'].year


def get_site_title():
    """
    Helper function to return the config site title, if it exists
    @return: str site title
    """
    return config.get("ckanext.doi.site_title")


def now():
    return datetime.now()


def can_request_doi(user, data):
    '''
    Determine whether the user can request a doi for a package owned by an
    organization, based on roles defined in the config.
    '''

    # If we can request doi outside of orgs, allow everyone to request.
    if config.get('ckanext.doi.doi_request_only_in_orgs') is False:
        return True

    org_id = data.get('owner_org') or data.get('group_id', None)

    if user:
        user_obj = toolkit.get_action('user_show')(
            data_dict={'id': user})
        # Sysadmins can do anything
        if user_obj['sysadmin']:
            return True

    # We need a user and org
    if not user or not org_id:
        return False

    # Roles authorized if ckanext.doi.doi_request_roles_in_orgs if not defined
    # in config.
    default_roles = "admin editor"

    # Is the user's role in the allowed roles list?
    user_role = authz.users_role_for_group_or_org(org_id, user)
    if user_role in config.get("ckanext.doi.doi_request_roles_in_orgs",
                               default_roles).split():
        return True

    return False
