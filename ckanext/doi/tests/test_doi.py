from logging import getLogger
from pylons import config
from nose.tools import assert_equal, assert_true, assert_false, assert_raises

from ckan.tests import helpers
from ckan.tests import factories

from ckanext.doi.api import get_doi_api
from ckanext.doi.api import datacite_api, ezid_api
import ckanext.doi.lib as doi_lib
from ckanext.doi.exc import DOIAPITypeNotKnownError, DOIMetadataException

log = getLogger(__name__)


class TestDOI(helpers.FunctionalTestBase):
    """
    Test creating DOIs
    nosetests -s --ckan --with-pylons=/Users/bens3/Projects/NHM/DataPortal/etc/default/test-core.ini ckanext.doi
    """

    def test_doi_config(self):
        """
        Test we are receiving params from the config file
        :return:
        """
        account_name = config.get("ckanext.doi.account_name")
        account_password = config.get("ckanext.doi.account_password")
        assert_false(account_name is None)
        assert_false(account_password is None)

    def test_doi_create_identifier(self):
        '''
        Test a DOI has been created with the package.
        '''
        # creating the package should also create a DOI instance
        pkg = factories.Dataset(author='Ben')

        # let's get it
        doi = doi_lib.get_doi(pkg['id'])

        # Make sure we have a DOI model
        assert_true(isinstance(doi, doi_lib.DOI))

        # And the package ID is correct
        assert_equal(doi.package_id, pkg['id'])

        # And published should be none
        assert_true(doi.published is None)

    def test_doi_metadata(self):
        '''
        Test the creation and validation of metadata
        '''
        pkg = factories.Dataset(author='Ben')

        doi = doi_lib.get_doi(pkg['id'])

        # Build the metadata dict to pass to DataCite service
        metadata_dict = doi_lib.build_metadata(pkg, doi)

        # Perform some basic checks against the data - we require at the very
        # least title and author fields - they're mandatory in the DataCite
        # Schema This will only be an issue if another plugin has removed a
        # mandatory field
        doi_lib.validate_metadata(metadata_dict)

    def test_doi_metadata_missing_author(self):
        '''Validating a DOI created from a package with no author will raise
        an exception.'''
        pkg = factories.Dataset()

        doi = doi_lib.get_doi(pkg['id'])

        # Build the metadata dict to pass to DataCite service
        metadata_dict = doi_lib.build_metadata(pkg, doi)

        # No author provided when creating dataset, so raise exception
        assert_raises(DOIMetadataException, doi_lib.validate_metadata,
                      metadata_dict)

    def test_get_doi_api_returns_correct_default_api_interface(self):
        '''Calling get_doi_api returns the correct api interface when nothing
        has been set for ckanext.doi.api_provider'''
        # default api is DataCite.
        doi_api = get_doi_api()
        assert_true(isinstance(doi_api, datacite_api.DOIDataCiteAPI))

    @helpers.change_config('ckanext.doi.api_provider', 'ezid')
    def test_get_doi_api_returns_correct_config_set_api_interface(self):
        '''Calling get_doi_api will return the correct api interface when
        ckanext.doi.api_provider has been set'''
        # api is the correct interface class for EZID
        doi_api = get_doi_api()

        assert_true(isinstance(doi_api, ezid_api.DOIEzidAPI))

    @helpers.change_config('ckanext.doi.api_provider', 'notatrueinterface')
    def test_get_doi_api_returns_correct_config_set_error_api_interface(self):
        '''Calling get_doi_api with an inproper ckanext.doi.api_provider set will
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
    #
    # def create_dataset(self):
    #     """
    #     TODO: Create a dataset and assert DOI exists
    #
    #     ctd.CreateTestData.create() creates using the model and bypasses
    #     plugin hooks - so we'll create using CKAN actions and then text the DOI exists
    #
    #     :return:
    #     """
    #     pass
