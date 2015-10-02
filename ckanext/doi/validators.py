import ckan.plugins.toolkit as toolkit
import ckan.lib.navl.dictization_functions as df
from ckanext.doi.helpers import can_request_doi_in_org

import logging
log = logging.getLogger(__name__)

Invalid = df.Invalid
_ = toolkit._


def doi_requester(key, data, errors, context):
    '''Requester must be authorized to request DOIs.'''

    # get owner_org
    owner_org = data.get(('owner_org',))

    # check whether user can request doi
    if not can_request_doi_in_org(owner_org) and data.get(('id',)):
        # get the original pkg
        pkg = toolkit.get_action('package_show')(
            data_dict={'id': data[('id',)]})

        # pass the original value to the data dict so it remains the same.
        data[key] = pkg.get(key[0])
        return
    else:
        log.info('user will be able to request doi')

    return
