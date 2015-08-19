ckanext-doi
===========

Overview
--------

CKAN extension for assigning a digital object identifier (DOI) to datasets, using the EZID DOI service.

When a new dataset is created it is assigned a new DOI. This DOI will be in the format:
 
http://dx.doi.org/[prefix]/[random 7 digit integer]

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

```python
ckanext.doi.account_name =
ckanext.doi.account_password =
ckanext.doi.prefix = 
ckanext.doi.publisher = 
ckanext.doi.test_mode = True or False
ckanext.doi.site_url =  # Defaults to ckan.site_url if not set 
ckanext.doi.site_title = # Optional - site title to use in the citation - eg Natural History Museum Data Portal (data.nhm.ac.uk)
```

Account name, password and prefix will be provided by your DataCite provider.
 
Publisher is the name of the publishing institution - eg: Natural History Museum.

The site URL is used to build the link back to the dataset:

http://[site_url]/datatset/package_id

If site_url is not set, ckan.site_url will be used instead.


If test mode is set to true, the DOIs will use the EZID test prefix 10.5072/FR2

To delete all test prefixes, use the command:

```python
paster doi delete-tests -c /etc/ckan/default/development.ini
```
