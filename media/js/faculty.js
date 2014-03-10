$(document).ready(function(){
  /* date pickers for date inputs */
  /* XXX: Surely we can just pick a CSS class to use instead? */
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

});

function event_filter_update() {
  var cat = $('input:radio[name=category]:checked').val();
  var table = $('#career_event_table').dataTable( {
    "bRetrieve": true,
  } );

  $.fn.dataTableExt.afnFiltering.pop();
  $.fn.dataTableExt.afnFiltering.push(function (oSettings, aData, iDataIndex) {
    if ( oSettings.nTable.id != 'career_event_table' ) {
      return true;
    }

    var row = $(table.fnGetNodes(iDataIndex));
    if ( cat === 'all' ) {
      return true;
    } else if ( row.hasClass(cat) ) {
      return true;
    } else {
      return false;
    }
  });

  table.fnDraw();
}
