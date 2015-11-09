/* Reveals/Hides the DOI prefix radios based on status of checkbox
 *
 */
this.ckan.module('doi-reveal-choices', function ($, _) {
  return {
    currentValue: true,
    options: {
      checkbox: $('#field-auto_doi_identifier'),
      reveal: $('#doi-choices'),
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
        this.options.reveal.slideDown();
      } else {
        this.options.reveal.slideUp();
      }
    }
  };
});
