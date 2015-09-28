/* Disables/Enables the DOI field based on status of checkbox
 *
 */
this.ckan.module('doi-disable-field', function ($, _) {
  return {
    currentValue: true,
    options: {
      checkbox: $('#field-auto_doi_identifier'),
      field: $('#field-doi_identifier'),
      currentValue: null
    },
    initialize: function() {
      $.proxyAll(this, /_on/);
      this.options.currentValue = this.options.checkbox.prop('checked');
      this.options.checkbox.on('change', this._onCheckboxChange);
      this._onCheckboxChange();
    },
    _onCheckboxChange: function() {
      var value = this.options.checkbox.prop('checked');
      if (value) {
        this.options.field
          .prop('readonly', true);
      } else {
        this.options.field
          .prop('readonly', false);
      }
    }
  };
});
