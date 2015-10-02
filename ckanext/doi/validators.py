import ckan.plugins.toolkit as toolkit
from ckanext.doi.helpers import can_request_doi

import logging
log = logging.getLogger(__name__)

_ = toolkit._


def doi_requester(key, data, errors, context):
    '''Requester must be authorized to request DOIs.'''

    user = context.get('user')
    # check whether user can request doi
    if not can_request_doi(user, data):
        log.info('User not able to request doi')
        # get the original pkg
        try:
            pkg = toolkit.get_action('package_show')(
                data_dict={'id': data[('id',)]})
        except toolkit.ValidationError:
            data[key] = None
        else:
            # pass the original value to the data dict so it remains the same.
            data[key] = pkg.get(key[0])
    else:
        log.info('user able to request doi')

    return
