from pylons import config
from paste.deploy.converters import asbool

from ckanext.doi.api import datacite_api, ezid_api
from ckanext.doi.exc import DOIAPITypeNotKnownError


TEST_PREFIX = '10.5072'


def get_test_mode():
    """
    Get test mode as boolean
    @return:
    """
    return asbool(config.get("ckanext.doi.test_mode", True))


def get_prefix():
    """
    Get the prefix to use for DOIs
    @return: test prefix if we're in test mode, otherwise config prefix setting
    """

    return TEST_PREFIX if get_test_mode() else config.get("ckanext.doi.prefix")


def get_api_type():
    '''Get the api type to use from the config. Default is datacite.'''
    return config.get('ckanext.doi.api_provider', 'datacite')


def _get_api_interface_from_list(apis):
    try:
        return apis[get_api_type()]()
    except KeyError:
        raise DOIAPITypeNotKnownError("No known DOI API type for: {0}"
                                      .format(get_api_type()))


def get_metadata_api():
    '''Return the appropriate api interface class for the passed api type.'''
    apis = {
        'datacite': datacite_api.MetadataDataCiteAPI,
        'ezid': ezid_api.MetadataEzidAPI
    }
    return _get_api_interface_from_list(apis)


def get_doi_api():
    '''Return the appropriate api interface class for the passed api type.'''
    apis = {
        'datacite': datacite_api.DOIDataCiteAPI,
        'ezid': ezid_api.DOIEzidAPI
    }
    return _get_api_interface_from_list(apis)
