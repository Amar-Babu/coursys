$(document).ready(function(){
  /* date pickers for date inputs */
  var dates = $('.date-input');
  dates.datepicker({
    dateFormat: 'yy-mm-dd',
    changeMonth: true,
    changeYear: true,
    });

  /* move template help around the page for memo template editing */
  $('#template-help').each(function() {
    $(this).css('float', 'right');
    $(this).insertBefore($('#id_template_text'));
  });

  /* The Semester part of the Semester date picker shouldn't be required regardless of
  if the whole field is.  Make sure the browser doesn't enforce that one, in case someone puts
  in a date without a semester code.
   */
  $('input.semester-input.semester-start').removeAttr('required');
});

function event_filter_update(datatable) {
  if ( $('input:radio[name=category]').length == 0 ) {
    // if form hidden, don't filter
    return;
  }

  var cat = $('input:radio[name=category]:checked').val();
  var table = $('#' + datatable).DataTable( {
    "retrieve": true,
  } );
  $.fn.dataTable.ext.search = [];
  $.fn.dataTable.ext.search.push(function(settings, data, i) {
    if ( settings.nTable.id != datatable || cat === 'all' ) {
      return true;
    }
    var row = table.row(i).node();
    return $(row).hasClass(cat);
  });

  table.draw();
}

function numberWithCommas(x) {
    // Based on http://stackoverflow.com/questions/2901102/how-to-print-a-number-with-commas-as-thousands-separators-in-javascript
    return x.toFixed(2).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
