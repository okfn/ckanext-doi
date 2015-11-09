ckanext-doi
===========

Overview
--------

CKAN extension for assigning a digital object identifier (DOI) to datasets, using the EZID DOI service.

When a new dataset is created it is assigned a new DOI. This DOI will be in the format:
 
`http://dx.doi.org/[prefix]/[random 7 digit integer]`

If the new dataset is active and public, the DOI and metadata will be registered with EZID.
 
If the dataset is draft or private, the DOI will not be registered.  When the
dataset is made active & public, the DOI will be submitted. This allows
datasets to be embargoed, but still provides a DOI to be referenced in
publications.

You will need an account with EZID DOI service provider to use this extension.


Installation
------------

To install ckanext-doi, activate your CKAN virtualenv and do:

```sh
git clone https://github.com/okfn/ckanext-doi.git
cd ckanext-doi
python setup.py develop
pip install -r requirements.txt
```

It will only work if you have signed up for an account with EZID.  

You will need a development / test account to use this plugin in test mode.


DOI Metadata
------------

Uses DataCite Metadata Schema v 3.1 https://schema.datacite.org/meta/kernel-3.1/index.html

Dataset package fields and CKAN config settings are mapped to the DataCite Schema  

|CKAN Dataset Field                 |DataCite Schema
|--- | ---
|dataset:title                      |title
|dataset:creator                    |author
|config:ckanext.doi.publisher       |publisher
|dataset:notes                      |description
|resource formats                   |format
|dataset:tags                       |subject
|dataset:licence (title)            |rights
|dataset:version                    |version
|dataset:extras spacial             |geo_box


DataCite title and author are mandatory metadata fields, so dataset title and creator fields are made required fields. 
This has been implemented in the theme layer, with another check in IPackageController.after_update, which raises
a DOIMetadataException if the title or author fields do not exist. 

It is recommended plugins implementing DOIs add additional validation checks to their schema.


Configuration
-------------

```ini
ckanext.doi.account_name =
ckanext.doi.account_password =
# if offering a single prefix and shoulder
ckanext.doi.prefix = 10.5072
ckanext.doi.shoulder = FK2
# or multiple prefixes and shoulders can be defined in a .json file (in module-path:file format)
ckanext.doi.prefix_choices = ckanext.doi.prefixes:my-prefixes.json
ckanext.doi.publisher = 
ckanext.doi.test_mode = True or False
ckanext.doi.site_url =  # Defaults to ckan.site_url if not set 
ckanext.doi.site_title = # Optional - site title to use in the citation - eg Natural History Museum Data Portal (data.nhm.ac.uk)

# If true, DOI request fields will only be available to datasets made as part
# of an organization.
ckanext.doi.doi_request_only_in_orgs = true

# A space separated list of roles within an organization that can request DOIs.
# Only applies if ckanext.doi.doi_request_only_in_orgs is True. Default is
# 'admin editor'
ckanext.doi.doi_request_roles_in_orgs = admin
```

Account name, password and prefix will be provided by your DataCite provider.
 
Publisher is the name of the publishing institution - eg: Natural History Museum.

If only a single prefix and shoulder is available to dataset authors, this can be set with `ckanext.doi.prefix`, e.g.

```ini
ckanext.doi.prefix = 10.5072
ckanext.doi.shoulder = FK2
```

If multiple prefixes and/or shoulders are available, these can be defined in a separate .json file, which should be located in the directory `ckanext/doi/prefixes/`, defined by the `ckanext.doi.prefix_choices` setting. The file should be formatted like the following:

```json
[
    {
        "label": "My Organization's Open Data Dept",
        "prefix": "10.5072",
        "shoulder": "D1"
    },
    {
        "label": "My Organization's Science Dept",
        "prefix": "10.5072",
        "shoulder": "SC1"
    }
]
```

These options will be available to choose as prefixes when automatically assigning a DOI to a dataset.

**Note**: If `ckanext.doi.prefix_choices` is present, `ckanext.doi.prefix` and `ckanext.doi.shoulder` will be ignored.

The site URL is used to build the link back to the dataset:

http://[site_url]/datatset/package_id

If site_url is not set, ckan.site_url will be used instead.

If test mode is set to true, the DOIs will use the EZID test prefix 10.5072/FK2

To delete all test prefixes, use the command:

```sh
paster doi delete-tests -c /etc/ckan/default/development.ini
```
