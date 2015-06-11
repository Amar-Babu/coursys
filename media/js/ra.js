var default_hours = 80;

function ra_autocomplete() {
  var regexp = /(,.*)/;
  var label;
  $('#id_person').each(function() {
    $(this).autocomplete({
      source:'/data/students',
      minLength: 2,
      select: function(event, ui){
        $(this).data("val", ui.item.value);
        label = ui.item.label.replace(regexp, "")
        $('#label_person_name').text(" " + label);
        update_person($(this).data("val"));
      },
      change: update_person,
    });
  });
}

function update_lump_sum() {
  var lump_sum = parseFloat($("#id_lump_sum_pay").val());
  var num_periods = parseFloat($("#id_pay_periods").val());
  var num_hours = parseFloat($("#id_hours").val());
  $("#id_hourly_pay").val((lump_sum / (num_periods * num_hours)).toFixed(2));
  $("#id_biweekly_pay").val((lump_sum / num_periods).toFixed(2));  
}

function update_biweekly() {
  var biweekly = parseFloat($("#id_biweekly_pay").val());
  var num_periods = parseFloat($("#id_pay_periods").val());
  var num_hours = parseFloat($("#id_hours").val());
  $("#id_lump_sum_pay").val((biweekly * num_periods).toFixed(2));
  $("#id_hourly_pay").val((biweekly / num_hours).toFixed(2));
}

function update_hours() {
  var lump_sum = parseFloat($("#id_lump_sum_pay").val());
  var num_periods = parseFloat($("#id_pay_periods").val());
  var num_hours = parseFloat($("#id_hours").val());
  $("#id_hourly_pay").val((lump_sum / (num_periods * num_hours)).toFixed(2));
  $("#id_biweekly_pay").val((lump_sum / num_periods).toFixed(2));
  $("#id_lump_sum_hours").val((num_hours * num_periods).toFixed(1));
}

function update_pay_periods_pay() {
  var lump_sum = parseFloat($("#id_lump_sum_pay").val());
  var num_periods = parseFloat($("#id_pay_periods").val());
  var num_hours = parseFloat($("#id_hours").val());
  $("#id_hourly_pay").val((lump_sum / (num_periods * num_hours)).toFixed(2));
  $("#id_biweekly_pay").val((lump_sum / num_periods).toFixed(2));
  $("#id_lump_sum_hours").val((num_hours * num_periods).toFixed(1));
}

function update_lump_hours() {
  var lump_hours = parseFloat($("#id_lump_sum_hours").val());
  var num_periods = parseFloat($("#id_pay_periods").val());
  var lump_sum = parseFloat($("#id_lump_sum_pay").val());
  $("#id_hours").val((lump_hours/num_periods).toFixed(1));
  $("#id_hourly_pay").val((lump_sum/lump_hours).toFixed(2));
}

function update_hourly() {
  var hourly = parseFloat($("#id_hourly_pay").val());
  var num_periods = parseFloat($("#id_pay_periods").val());
  var num_hours = parseFloat($("#id_hours").val());
  $("#id_lump_sum_pay").val((hourly * num_hours * num_periods).toFixed(2));
  $("#id_biweekly_pay").val((hourly * num_hours).toFixed(2));
}

function update_pay_frequency() {
	var v = $("#id_pay_frequency").val();
	if ( v == 'L' ) {
		$("#id_hourly_pay").prop('disabled', true);
		$("#id_biweekly_pay").prop('disabled', true);
		$("#id_hours").prop('disabled', true).val(1);
		$("#id_pay_periods").prop('disabled', true).val(1);
		update_lump_sum();
	} else {
		$("#id_hourly_pay").prop('disabled', false);
		$("#id_biweekly_pay").prop('disabled', false);
		$("#id_hours").prop('disabled', false);
		$("#id_pay_periods").prop('disabled', false);
	}
}

function update_pay_periods() {
	var start_text = $("#id_start_date").val();
	var end_text = $("#id_end_date").val();
	var url = payperiods_url + "?start=" + start_text + "&end=" + end_text;
	$.ajax({
		url: url,
		success: function(data) {
		    $("#id_pay_periods").val(data);
			if ( $("#id_pay_frequency").val() == 'L' ) {
    			var lump_hours = parseFloat($("#id_lump_sum_hours").val());
    			var lump_sum = parseFloat($("#id_lump_sum_pay").val());
    			var num_periods = parseFloat(data);
                $("#id_hours").val((lump_hours/num_periods).toFixed(1));
                $("#id_hourly_pay").val((lump_sum/lump_hours).toFixed(2));
			} else {
    			var hours = parseFloat($("#id_hours").val());
    			var num_periods = parseFloat(data);
    			if ( isNaN(hours) ) {
    			    hours = default_hours;
    			}
         	    $("#id_hours").val(hours);
    		    $("#id_lump_sum_hours").val((num_periods*hours).toFixed(1));
			}
		},
	});
}


function update_person() {
	emplid = $('#id_person').first().val();
	// update program list
	get_person_info(emplid);
	// get scholarships
    $.getJSON("/data/scholarships/" + emplid, function(json) {
    var options = '<option value="">—</option>';
    for (var i=0; i < json.length; i++) {
      options += '<option value="' + json[i].value +'">' + json[i].display + '</option>';
    }
    $('#id_scholarship').html(options);
  });
}

function get_person_info(emplid) {
	$('div#programs').remove();
	$('dl.dlform').first().before('<div id="programs">...</div>');	
	$.ajax({
		url: personinfo_url + '?emplid=' + emplid,
		success: function(data, textStatus, jqXHR) {
			var html = '';
			html += '<h3>Program(s)</h3><ul>';
			if ( data['programs'].length == 0) {
				html += '<li class="empty">No grad program in system</li>';
			} else {
				$(data['programs']).each(function(e,prog) {
					html += '<li>';
					html += prog['program'] + ', ' + prog['unit'] + ' (' + prog['status'] + ')';
					html += '</li>';
				});
			}
			html += '</ul>';

	        if (data['citizen']) {
	        	html += '<p>Citizenship: ' + data['citizen'] + '</p>'
	        } else {
	        	html += '<p>Citizenship: unknown</p>'	        	
	        }

			$('div#programs').html(html);
		},
	})
}

var table;

function server_params() {
	// build the extra GET parameters that will go in the datatables data request (by inspecting the filter form)
	var params = [];
	return params;
}

function ra_browser_setup(my_url) {
  table = $('#ra_table').dataTable( {
    'jQueryUI': true,
    'pagingType': 'full_numbers',
    'pageLength' : 20,
    //'order': [[0,'asc'],[4,'desc']],
    'processing': true,
    'serverSide': true,
    'sAjaxSource': my_url + '?tabledata=yes',
  } );

}

$(document).ready(function() {
  name_label = document.createElement("span");
  name_label.id = "label_person_name";
  $('#id_person').parent().append(name_label);
  $("id_person").focus();
  ra_autocomplete('id_person');
  $("#id_start_date").datepicker({'dateFormat': 'yy-mm-dd'});
  $("#id_end_date").datepicker({'dateFormat': 'yy-mm-dd'});
  $("#id_lump_sum_pay").change(update_lump_sum);
  $("#id_lump_sum_hours").change(update_lump_hours);
  $("#id_biweekly_pay").change(update_biweekly);
  $("#id_pay_periods").change(update_pay_periods_pay);
  $("#id_hourly_pay").change(update_hourly);
  $("#id_hours").change(update_hours);
  $("#id_pay_frequency").change(update_pay_frequency);
  update_pay_frequency();
  $("#id_person").change(update_person);
  $("#id_start_date").change(update_pay_periods);
  $("#id_end_date").change(update_pay_periods);
  if ( typeof payperiods_url !== 'undefined' ) {
    update_pay_periods();
  }
  if ( typeof emplid !== 'undefined' ) {
  	get_person_info(emplid);
  }
});