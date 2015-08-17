from pylons import config

from ckanext.doi.api import datacite_api, ezid_api
from ckanext.doi.exc import DOIAPITypeNotKnownError


def get_api_type():
    '''Get the api type to use from the config. Default is datacite.'''
    return config.get('ckanext.doi.api_type', 'datacite')


def _get_api_interface_from_list(apis):
    try:
        return apis[get_api_type()]()
    except KeyError:
        raise DOIAPITypeNotKnownError("No known DOI API type for: {0}"
                                      .format(get_api_type()))


def get_metadata_api():
    '''Return the appropriate api interface class for the passed api type.'''
    apis = {
        'datacite': datacite_api.MetadataDataCiteAPI
    }
    return _get_api_interface_from_list(apis)


def get_doi_api():
    '''Return the appropriate api interface class for the passed api type.'''
    apis = {
        'datacite': datacite_api.DOIDataCiteAPI,
        'ezid': ezid_api.DOIEzidAPI
    }
    return _get_api_interface_from_list(apis)
