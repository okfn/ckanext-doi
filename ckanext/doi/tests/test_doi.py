from logging import getLogger
from pylons import config
from nose.tools import (assert_equal, assert_true,
                        assert_false, assert_raises, assert_not_equal)

from ckan.tests import helpers
from ckan.tests import factories
import ckan.plugins.toolkit as toolkit

from ckanext.doi.api import get_doi_api
from ckanext.doi.api import ezid_api
import ckanext.doi.lib as doi_lib
from ckanext.doi.exc import DOIAPITypeNotKnownError, DOIMetadataException

log = getLogger(__name__)


class TestDOICreate(helpers.FunctionalTestBase):

    def test_doi_config(self):
        '''
        Test we are receiving params from the config file
        :return:
        '''
        account_name = config.get("ckanext.doi.account_name")
        account_password = config.get("ckanext.doi.account_password")
        assert_false(account_name is None)
        assert_false(account_password is None)

    def test_doi_auto_create_identifier(self):
        '''Test a DOI has been created with the package.'''
        # creating the package should also create a DOI instance
        pkg = factories.Dataset(author='Ben', auto_doi_identifier=True)

        # let's get it
        doi = doi_lib.get_doi(pkg['id'])

        # Make sure we have a DOI model
        assert_true(isinstance(doi, doi_lib.DOI))

        # And the package ID is correct
        assert_equal(doi.package_id, pkg['id'])

        # And published should be none
        assert_true(doi.published is None)

    def test_doi_not_created_when_manual_checked(self):
        '''If auto_doi_identifier is false, don't create a doi.'''
        pkg = factories.Dataset(author='Ben', auto_doi_identifier=False)

        doi = doi_lib.get_doi(pkg['id'])

        assert_true(doi is None)

    def test_doi_auto_created_when_field_not_defined(self):
        '''On package creation, a DOI object should be created and
        doi_identifier field should be populated with the DOI id.'''
        pkg = factories.Dataset(author='Ben', auto_doi_identifier=True)

        retrieved_pkg = helpers.call_action('package_show', id=pkg['id'])

        doi = doi_lib.get_doi(pkg['id'])

        assert_equal(doi.identifier, retrieved_pkg['doi_identifier'])

    def test_doi_auto_created_when_field_is_defined(self):
        '''On package creation, DOI object should be created with the
        doi_identifier field value. A passed doi_identifier is ignored.'''
        pkg = factories.Dataset(author='Ben', doi_identifier='example-doi-id',
                                auto_doi_identifier=True)

        retrieved_pkg = helpers.call_action('package_show', id=pkg['id'])

        doi = doi_lib.get_doi(pkg['id'])

        assert_not_equal(retrieved_pkg['doi_identifier'], 'example-doi-id')

        assert_equal(doi.identifier, retrieved_pkg['doi_identifier'])

    def test_doi_not_created_when_field_is_defined_manual_checked(self):
        '''On package creation, DOI object should not be created if
        auto_doi_identifier is false.'''
        pkg = factories.Dataset(author='Ben', doi_identifier='example-doi-id',
                                auto_doi_identifier=False)

        retrieved_pkg = helpers.call_action('package_show', id=pkg['id'])

        doi = doi_lib.get_doi(pkg['id'])

        assert_equal(retrieved_pkg['doi_identifier'], 'example-doi-id')

        assert_true(doi is None)

    def test_doi_metadata(self):
        '''
        Test the creation and validation of metadata
        '''
        pkg = factories.Dataset(author='Ben', auto_doi_identifier=True)

        doi = doi_lib.get_doi(pkg['id'])

        # Build the metadata dict to pass to DataCite service
        metadata_dict = doi_lib.build_metadata(pkg, doi)

        # Perform some basic checks against the data - we require at the very
        # least title and author fields - they're mandatory in the DataCite
        # Schema. This will only be an issue if another plugin has removed a
        # mandatory field
        doi_lib.validate_metadata(metadata_dict)

    def test_package_author_required(self):
        '''Author is a required field, because DOIs require it.'''

        assert_raises(toolkit.ValidationError, factories.Dataset)

    def test_doi_metadata_missing_author(self):
        '''Validating a DOI created from a package with no author will raise
        an exception.'''

        pkg = factories.Dataset(auto_doi_identifier=True, author='My Author')

        doi = doi_lib.get_doi(pkg['id'])

        # remove author value from pkg_dict before attempting validation
        pkg['author'] = None

        # Build the metadata dict to pass to DataCite service
        metadata_dict = doi_lib.build_metadata(pkg, doi)

        # No author in pkg_dict, so exception should be raised
        assert_raises(DOIMetadataException, doi_lib.validate_metadata,
                      metadata_dict)


class TestDOIFieldsDisplay(helpers.FunctionalTestBase):

    '''Tests for when to display the DOI fields in the dataset form'''

    @helpers.change_config('ckanext.doi.doi_request_only_in_orgs', False)
    def test_doi_fields_new_unowned_dataset_only_in_orgs_false(self):
        '''The doi fields will display for unowned datasets when
        doi_request_only_in_orgs is False.'''
        app = self._get_test_app()
        response = app.get(url=toolkit.url_for(controller='package',
                                               action='new'))

        assert_true('doi_identifier' in response.forms['dataset-edit'].fields)

    @helpers.change_config('ckanext.doi.doi_request_only_in_orgs', True)
    def test_doi_fields_new_unowned_dataset_only_in_orgs_true(self):
        '''The doi fields will not display for unowned datasets when
        doi_request_only_in_orgs is True.'''
        app = self._get_test_app()
        response = app.get(url=toolkit.url_for(controller='package',
                                               action='new'))

        assert_true('doi_identifier' not in
                    response.forms['dataset-edit'].fields)

    @helpers.change_config('ckanext.doi.doi_request_only_in_orgs', False)
    def test_doi_fields_new_owned_dataset_only_in_orgs_false(self):
        '''DOI fields will display for owned datasets (datasets made as part
        of an org) when doi_request_only_in_orgs is False.'''
        app = self._get_test_app()
        sysadmin = factories.Sysadmin()

        org = factories.Organization()
        url = '{0}?group={1}'.format(toolkit.url_for(controller='package',
                                                     action='new'),
                                     org['id'])
        env = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        response = app.get(url=url, extra_environ=env)

        assert_true('doi_identifier' in response.forms['dataset-edit'].fields)

    @helpers.change_config('ckanext.doi.doi_request_only_in_orgs', True)
    def test_doi_fields_new_owned_dataset_only_in_orgs_true(self):
        '''DOI fields will display for owned datasets (datasets made as part
        of an org) when doi_request_only_in_orgs is True.'''
        app = self._get_test_app()
        sysadmin = factories.Sysadmin()

        org = factories.Organization()
        url = '{0}?group={1}'.format(toolkit.url_for(controller='package',
                                                     action='new'),
                                     org['id'])
        env = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        response = app.get(url=url, extra_environ=env)

        assert_true('dataset-edit' in response.forms)
        assert_true('doi_identifier' in response.forms['dataset-edit'].fields)


class TestDOIAPIInterface(object):

    def test_get_doi_api_returns_correct_default_api_interface(self):
        '''Calling get_doi_api returns the correct api interface when nothing
        has been set for ckanext.doi.api_provider'''
        # default api is EZID.
        doi_api = get_doi_api()
        assert_true(isinstance(doi_api, ezid_api.DOIEzidAPI))

    @helpers.change_config('ckanext.doi.api_provider', 'ezid')
    def test_get_doi_api_returns_correct_config_set_api_interface(self):
        '''Calling get_doi_api will return the correct api interface when
        ckanext.doi.api_provider has been set'''
        # api is the correct interface class for EZID
        doi_api = get_doi_api()
        assert_true(isinstance(doi_api, ezid_api.DOIEzidAPI))

    @helpers.change_config('ckanext.doi.api_provider', 'notatrueinterface')
    def test_get_doi_api_returns_correct_config_set_error_api_interface(self):
        '''Calling get_doi_api with an improper ckanext.doi.api_provider set will
        raise an exception.'''

        assert_raises(DOIAPITypeNotKnownError, get_doi_api)


    # def test_doi_publish_datacite(self):

    #     import ckanext.doi.lib as doi_lib

    #     doi = doi_lib.get_doi(self.package_dict['id'])

    #     if not doi:
    #         doi = doi_lib.create_unique_identifier(self.package_dict['id'])

    #     # Build the metadata dict to pass to DataCite service
    #     metadata_dict = doi_lib.build_metadata(self.package_dict, doi)

    #     # Perform some basic checks against the data - we require at the very least
    #     # title and author fields - they're mandatory in the DataCite Schema
    #     # This will only be an issue if another plugin has removed a mandatory field
    #     doi_lib.validate_metadata(metadata_dict)

    #     doi_lib.publish_doi(self.package_dict['id'], **metadata_dict)
