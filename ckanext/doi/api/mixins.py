from xmltodict import unparse

import ckan.plugins as p

from ckanext.doi.interfaces import IDoi


class MetadataToDataCiteXmlMixin(object):

    '''Provide a static method to transform passed metadata to XML that
    adheres to the DataCite Metadata Scheme schema.'''

    @staticmethod
    def metadata_to_xml(identifier, title, creator, publisher, publisher_year,
                        **kwargs):
        '''
        Pass in variables and return XML in the format ready to send to
        DataCite API

        @param identifier: DOI
        @param title: A descriptive name for the resource
        @param creator: The author or producer of the data. There may be
            multiple Creators, in which case they should be listed in order of
            priority
        @param publisher: The data holder. This is usually the repository or
            data centre in which the data is stored
        @param publisher_year: The year when the data was (or will be) made
            publicly available.
        @param kwargs: optional metadata
        @return:
        '''

        # Make sure a var is a list so we can easily loop through it
        # Useful for properties were multiple is optional
        def _ensure_list(var):
            return var if isinstance(var, list) else [var]

        # Encode title ready for posting
        title = title.encode('unicode-escape')

        # Optional metadata properties
        subject = kwargs.get('subject')
        description = kwargs.get('description').encode('unicode-escape')
        size = kwargs.get('size')
        format = kwargs.get('format')
        version = kwargs.get('version')
        rights = kwargs.get('rights')
        geo_point = kwargs.get('geo_point')
        geo_box = kwargs.get('geo_box')

        # Optional metadata properties, with defaults
        resource_type = kwargs.get('resource_type', 'Dataset')
        language = kwargs.get('language', 'eng')

        # Create basic metadata with mandatory metadata properties
        xml_dict = {
            'resource': {
                '@xmlns': 'http://datacite.org/schema/kernel-3',
                '@xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                '@xsi:schemaLocation': 'http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd',
                'identifier': {'@identifierType': 'DOI', '#text': identifier},
                'titles': {
                    'title': {'#text': title}
                },
                'creators': {
                    'creator': [{'creatorName': c.encode('unicode-escape')}
                                for c in _ensure_list(creator)],
                },
                'publisher': publisher,
                'publicationYear': publisher_year,
            }
        }

        # Add subject (if it exists)
        if subject:
            xml_dict['resource']['subjects'] = {
                'subject': [c for c in _ensure_list(subject)]
            }

        if description:
            xml_dict['resource']['descriptions'] = {
                'description': {
                    '@descriptionType': 'Abstract',
                    '#text': description
                }
            }

        if size:
            xml_dict['resource']['sizes'] = {
                'size': size
            }

        if format:
            xml_dict['resource']['formats'] = {
                'format': format
            }

        if version:
            xml_dict['resource']['version'] = version

        if rights:
            xml_dict['resource']['rightsList'] = {
                'rights': rights
            }

        if resource_type:
            xml_dict['resource']['resourceType'] = {
                '@resourceTypeGeneral': 'Dataset',
                '#text': resource_type
            }

        if language:
            xml_dict['resource']['language'] = language

        if geo_point:
            xml_dict['resource']['geoLocations'] = {
                'geoLocation': {
                    'geoLocationPoint': geo_point
                }
            }

        if geo_box:
            xml_dict['resource']['geoLocations'] = {
                'geoLocation': {
                    'geoLocationBox': geo_box
                }
            }

        for plugin in p.PluginImplementations(IDoi):
            xml_dict = plugin.metadata_to_xml(xml_dict, kwargs)

        return unparse(xml_dict, pretty=True, full_document=False)
