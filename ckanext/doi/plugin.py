import os
import json
import inspect
import logging

import ckan.plugins as p
import ckan.logic as logic
from ckan import model
from ckanext.doi.model import doi as doi_model
from ckanext.doi.lib import (get_doi, delete_doi, publish_doi,
                             update_doi, create_unique_identifier,
                             get_site_url, build_metadata, validate_metadata)
from ckanext.doi.helpers import (package_get_year,
                                 now,
                                 get_site_title,
                                 can_request_doi,
                                 get_prefixes
                                 )
from ckanext.doi.validators import doi_requester, doi_prefix

get_action = logic.get_action

log = logging.getLogger(__name__)


class DOIPlugin(p.SingletonPlugin):
    '''
    CKAN DOI Extension
    '''
    p.implements(p.IConfigurable)
    p.implements(p.IConfigurer)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)

    def _load_json_module_path(self, json_path):
        '''
        Given a path like "ckanext.my_plugin:doi_prefixes.json" find the
        second part relative to the import path of the first
        '''
        module, file_name = json_path.split(':', 1)
        try:
            # __import__ has an odd signature
            m = __import__(module, fromlist=[''])
        except ImportError:
            return
        p = os.path.join(os.path.dirname(inspect.getfile(m)), file_name)
        if os.path.exists(p):
            return json.load(open(p))

    # IConfigurable

    def configure(self, config):
        '''
        Called at the end of CKAN setup.
        Create DOI table
        '''
        if model.package_table.exists():
            doi_model.doi_table.create(checkfirst=True)

    # IConfigurer

    def _load_prefixes(self, config):
        '''Load the contents of the file found at the `prefix_choices` option
        into the `_prefixes` property of the DOIPlugin class.'''
        DOIPlugin._prefixes = None
        config_prefixes = config.get('ckanext.doi.prefix_choices', None)
        if config_prefixes:
            DOIPlugin._prefixes = self._load_json_module_path(config_prefixes)

    def update_config(self, config):
        # Add templates
        p.toolkit.add_template_directory(config, 'theme/templates')

        p.toolkit.add_public_directory(config, 'theme/public')

        p.toolkit.add_resource('theme/fanstatic', 'doi')

        # if ckanext.doi.prefix_choices ignore doi.prefix and load the json
        self._load_prefixes(config)

    # IPackageController

    def _update_pkg_doi(self, context, pkg_id, doi_identifier):
        '''Update pkg['doi_identifier'] with the passed doi_identifier'''
        # Don't want after_update to run after this patch
        context.update({'no_after_update': True})
        # Add new doi_identifier to package
        get_action('package_patch')(context,
                                    {'id': pkg_id,
                                     'doi_identifier': doi_identifier})

    def after_create(self, context, pkg_dict):
        '''
        A new dataset has been created, so we need to create a new DOI. NB:
        This is called after creation of a dataset, and before resources have
        been added so state = draft
        @param context:
        @param pkg_dict:
        @return:
        '''
        if pkg_dict.get('auto_doi_identifier'):
            # create a doi and populate pkg.doi_identifier with it.
            prefix = pkg_dict.get('doi_prefix')
            doi = create_unique_identifier(pkg_dict['id'], prefix)
            self._update_pkg_doi(context, pkg_dict['id'], doi.identifier)

    def after_update(self, context, pkg_dict):
        '''
        Dataset has been created / updated. Check status of the dataset to
        determine if we should publish DOI.

        @param pkg_dict:
        @return: pkg_dict
        '''

        package_id = pkg_dict['id']
        # Load the local DOI
        doi = get_doi(package_id)

        # If we're not auto managing the doi, but there is a DOI object
        # associated with the package, delete it.
        if not pkg_dict.get('auto_doi_identifier') and doi:
            delete_doi(package_id)
            doi = None

        # We might be short circuiting the after_update
        if context.get('no_after_update') \
           or not pkg_dict.get('auto_doi_identifier'):
            return pkg_dict

        # If we don't have a DOI, create one.
        # This could happen if the DOI module is enabled after a dataset
        # has been created, or if a user has added their own on dataset
        # creation, but subsequently deleted it.
        if not doi:
            prefix = pkg_dict.get('doi_prefix')
            doi = create_unique_identifier(package_id, prefix)

        # ensure doi.identifier and pkg['doi_identifier'] are the same
        if doi.identifier != pkg_dict['doi_identifier']:
            self._update_pkg_doi(context, package_id, doi.identifier)

        # Is this active and public? If so we need to make sure we have an
        # active DOI
        if pkg_dict.get('state', 'active') == 'active' \
           and not pkg_dict.get('private', False):

            # Load the original package, so we can determine if user has
            # changed any fields
            orig_pkg_dict = get_action('package_show')(context,
                                                       {'id': package_id})

            # Metadata created isn't populated in pkg_dict - so copy from the
            # original
            pkg_dict['metadata_created'] = orig_pkg_dict['metadata_created']

            # Build the metadata dict to pass to DataCite service
            metadata_dict = build_metadata(pkg_dict, doi)

            # Perform some basic checks against the data - we require at the
            # very least title and author fields - they're mandatory in the
            # DataCite Schema This will only be an issue if another plugin has
            # removed a mandatory field
            validate_metadata(metadata_dict)

            # Is this an existing DOI? Update it
            if doi.published:
                # Before updating, check if any of the metadata has been
                # changed - otherwise we end up sending loads of revisions to
                # DataCite for minor edits Load the current version
                orig_metadata_dict = build_metadata(orig_pkg_dict, doi)
                # Check if the two dictionaries are the same
                if cmp(orig_metadata_dict, metadata_dict) != 0:
                    # Not the same, so we want to update the metadata
                    update_doi(package_id, **metadata_dict)

                # TODO: If editing a dataset older than 5 days, create DOI
                # revision

            # New DOI - publish to datacite
            else:
                publish_doi(package_id, **metadata_dict)

        return pkg_dict

    def after_show(self, context, pkg_dict):
        # Load the DOI ready to display
        doi = get_doi(pkg_dict['id'])
        if doi:
            pkg_dict['doi_status'] = True if doi.published else False
            pkg_dict['domain'] = get_site_url().replace('http://', '')

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'package_get_year': package_get_year,
            'now': now,
            'get_site_title': get_site_title,
            'can_request_doi': can_request_doi,
            'get_doi_prefixes': get_prefixes
        }


class DOIDatasetPlugin(p.SingletonPlugin, p.toolkit.DefaultDatasetForm):

    '''
    An IDatasetForm plugin to add a DOI field to the dataset schema.
    '''

    p.implements(p.IDatasetForm)
    p.implements(p.IValidators)

    # IDatasetForm

    def _modify_package_schema(self, schema):
        schema.update({
            'author': [
                p.toolkit.get_validator('not_empty')
            ],
            'auto_doi_identifier': [
                # p.toolkit.get_validator('ignore_missing'),
                p.toolkit.get_validator('boolean_validator'),
                p.toolkit.get_validator('doi_requester'),
                p.toolkit.get_converter('convert_to_extras'),
            ],
            'doi_identifier': [
                p.toolkit.get_validator('doi_requester'),
                p.toolkit.get_converter('convert_to_extras'),
            ],
            'doi_prefix': [
                p.toolkit.get_validator('doi_prefix'),
                p.toolkit.get_converter('convert_to_extras')
            ]
        })
        return schema

    def create_package_schema(self):
        schema = super(DOIDatasetPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(DOIDatasetPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(DOIDatasetPlugin, self).show_package_schema()
        schema.update({
            'author': [
                p.toolkit.get_validator('not_empty')
            ],
            'auto_doi_identifier': [
                p.toolkit.get_converter('convert_from_extras'),
                p.toolkit.get_validator('boolean_validator')
            ],
            'doi_identifier': [
                p.toolkit.get_converter('convert_from_extras')
            ],
            'doi_prefix': [
                p.toolkit.get_converter('convert_from_extras')
            ]
        })
        return schema

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    # IValidators

    def get_validators(self):
        return {
            'doi_requester': doi_requester,
            'doi_prefix': doi_prefix
            }
