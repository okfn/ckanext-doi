#!/usr/bin/env python
# encoding: utf-8
"""
Created by 'bens3' on 2013-06-21.
Copyright (c) 2013 'bens3'. All rights reserved.
"""


class DOIMetadataException(Exception):
    """
    Exception for DOI metadata errors - missing mandatory fields
    """
    pass


class DOIAPITypeNotKnownError(Exception):
    '''Exception when ckanext.doi.api_provider has been set to a value not known
    by the api.get_*_api methods'''
    pass
