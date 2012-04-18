function add(){
	var total_forms = $('#id_form-TOTAL_FORMS').val()*1;
	var max_forms = $('#id_form-MAX_NUM_FORMS').val()*1;
	if (total_forms < max_forms){
		newForm = $('#supervisor-form-0').clone(true);
		
		new_id=$(newForm).attr('id').replace('-0', '-' + total_forms);
		$(newForm).attr('id', new_id);
		
		formset_label = newForm.find('p[id$="label"]')
		formset_label.html('Supervisor ' + (total_forms+1) + ':');
		new_id=formset_label.attr('id').replace('-0', '-' + total_forms);
		formset_label.attr('id',new_id);
		
		newForm.find(':input').each(function() {
	        var new_name = $(this).attr('name').replace('-0-','-' + total_forms + '-');
	        var new_id = 'id_' + new_name;
       		$(this).attr({'name': new_name, 'id': new_id});	
        	$(this).val('');
        	if(new_name.indexOf('id')!=-1){
        		$(this).val(''); // ensures id gets cleared
        	}
	        if(new_id.indexOf('position')!=-1){
        		$(this).val((total_forms+1)); //increment position
	        }
	        if(new_name.indexOf("supervisor_0")!=-1){
	        	$(this).find('option').removeAttr('selected');
	        	// copy event handlers. For some reason, clone(true) is not cloning the handlers as it should.
	        	$(this).change(function(){
	        		processSelections($('select[id*="supervisor"]'));
					// exclude potential
					if($(this).attr('id').indexOf('pot')==-1){
						$('#'+$(this).attr('id').replace('supervisor_0','external')).val('');
					}
	        	})
	        }
	    });
	    	    
	    newForm.find('label').each(function() {
	        var new_for = $(this).attr('for').replace('-0-','-' + total_forms + '-');
	        $(this).attr('for', new_for);
	    });
	    
		$('#id_form-TOTAL_FORMS').val(total_forms+1);
		$('#supervisor-forms').append($(newForm));
		processSelections($('select[id*="supervisor"]'));
		if (total_forms+1 == max_forms){
			$('#add_btn').attr('disabled', true).css('background-color','#bba');
		}
	}
}

var currentSelections = new Object();

function processSelections(selectOptions){
	// store the current selections
	$(selectOptions).each(function(){
		currentSelections[$(this).attr('id')] = $(this).val();
	});
	
	// loop through each select dropdown and do the following:
	// 1. clear all disabled values
	// 2. disable currently selected values in other drop downs EXCEPT for the "Other" value
	
	$(selectOptions).each(function(i,ele){
		
	});
	$(selectOptions).each(function(i, ele){
		$(ele).find('option:disabled').attr('disabled',false);
		$.each(currentSelections,function(key,val){
			if(key != $(ele).attr('id') && val!=''){
				$(ele).find('option[value='+val+']').attr('disabled',true);
			}
		});
	});
 }
