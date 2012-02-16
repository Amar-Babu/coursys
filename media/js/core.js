function confirmSubmit(action) {
  return confirm("Are you sure you wish to " + action + "?");
}


/* jQuery Datatables sorting by mark (e.g. "4.5/10") */
function mark_cmp(x,y) {
  xn = parseFloat(x.split("/", 1), 10)
  yn = parseFloat(y.split("/", 1), 10)
  if (isNaN(xn) && isNaN(yn)) { return 0;
  } else if (isNaN(xn)) { return -1;
  } else if (isNaN(yn)) { return 1;
  } else {
    return ((xn < yn) ? -1 : ((xn > yn) ? 1 : 0));
  }    
}
jQuery.fn.dataTableExt.oSort['by-mark-asc']  = function(x,y) { return mark_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-mark-desc'] = function(x,y) { return mark_cmp(y,x) };

/* jQuery Datatables sorting ignoring any <a> (e.g. '<a href="foo">123</a>' sorts by '123') */
link_re = new RegExp('<a .+>(.+)</a>');
function nolink_cmp(x,y) {
  xc = link_re.exec(x);
  yc = link_re.exec(y);
  if ( xc == null && yc == null ) { return -0 }
  if ( xc == null ) { return -1; }
  if ( yc == null ) { return 1; }
  xc = xc[1];
  yc = yc[1];
  return ((xc < yc) ? -1 : ((xc > yc) ? 1 : 0));
}
jQuery.fn.dataTableExt.oSort['by-nolink-asc']  = function(x,y) { return nolink_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-nolink-desc'] = function(x,y) { return nolink_cmp(y,x) };

/* jQuery Datatables sorting combining nolink_cmp and mark_cmp (for marks in links) */
function nolinkmark_cmp(x,y) {
  xre = link_re.exec(x);
  yre = link_re.exec(y);
  xc = xre==null ? '' : xre[1];
  yc = yre==null ? '' : yre[1];
  return mark_cmp(xc,yc);
}
jQuery.fn.dataTableExt.oSort['by-nolinkmark-asc']  = function(x,y) { return nolinkmark_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-nolinkmark-desc'] = function(x,y) { return nolinkmark_cmp(y,x) };

/* jQuery Datatables sorting for letter grades in links */
letter_map = {"WE": 15, "WD": 15, "FX": 17, "DE": 12, "FD": 14, "GN": 16, "CN": 17, "C+": 6, "C-": 8, "A+": 0, "A-": 2, "A": 1, "C": 7, "B": 4, "AE": 17, "D": 9, "F": 11, "CC": 17, "IP": 16, "CF": 17, "N": 13, "P": 10, "AU": 17, "W": 15, "CR": 17, "B-": 5, "B+": 3} /* generated: see LETTER_POSITION in grades/models.py */
function letter_cmp(x,y) {
  xc = letter_map[x];
  yc = letter_map[y];
  if ( xc == null && yc == null ) { return 0 }
  if ( xc == null ) { return 1; }
  if ( yc == null ) { return -1; }
  return ((xc < yc) ? -1 : ((xc > yc) ? 1 : 0));
}
function nolinkletter_cmp(x,y) {
  xre = link_re.exec(x);
  yre = link_re.exec(y);
  xc = xre==null ? '' : xre[1];
  yc = yre==null ? '' : yre[1];
  return letter_cmp(xc,yc);
}
jQuery.fn.dataTableExt.oSort['by-nolinkletter-asc']  = function(x,y) { return nolinkletter_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-nolinkletter-desc'] = function(x,y) { return nolinkletter_cmp(y,x) };

jQuery.fn.dataTableExt.oSort['by-letter-asc']  = function(x,y) { return letter_cmp(x,y) };
jQuery.fn.dataTableExt.oSort['by-letter-desc'] = function(x,y) { return letter_cmp(y,x) };

// toggle display of news item bodies
function togglenews(e, elt) {
  var event = e || window.event;
  // http://www.quirksmode.org/js/events_properties.html
  var targ, i, more;
  if (event.target) targ = event.target;
  else if (event.srcElement) targ = event.srcElement;
  if (targ.nodeType == 3) // defeat Safari bug
    targ = targ.parentNode;
  
  newsitem = targ.parentNode.parentNode;
  var divs = newsitem.getElementsByTagName('div');
  for(i=0; i<divs.length; i++) {
     if ( divs[i].className == 'newsmore' ) {
       more = divs[i];
     }
  }
  if (window.getComputedStyle(more, null).getPropertyValue('display') == 'none') {
    more.style.display = "block";
    targ.innerHTML = "-";
  } else {
    more.style.display = "none";
    targ.innerHTML = "+";
  }
}

/* http://stackoverflow.com/questions/1418050/string-strip-for-javascript */
if(typeof(String.prototype.trim) === "undefined")
{
    String.prototype.trim = function() 
    {
        return String(this).replace(/^\s+|\s+$/g, '');
    };
}

/* jQuery Datatables sorting by something/nothing */
function mark_anything(x,y) {
  var xt = x.trim();
  var yt = y.trim();
  if ( xt == "" && yt == "") { return 0;
  } else if ( xt == "" ) { return 1;
  } else if ( yt == "" ) { return -1;
  } else { return 0; }    
}
jQuery.fn.dataTableExt.oSort['by-anything-asc']  = function(x,y) { return mark_anything(x,y) };
jQuery.fn.dataTableExt.oSort['by-anything-desc'] = function(x,y) { return mark_anything(y,x) };

/* jQuery Datatables sorting by marking link */
function mark_marklink(x,y) {
  var xp = x.indexOf("magnifier.png");
  var yp = y.indexOf("magnifier.png");
  console.log(x);
  console.log(xp);
  if ( xp == -1 && yp == -1) { return 0;
  } else if ( xp == -1 ) { return 1;
  } else if ( yp == -1 ) { return -1;
  } else { return 0; }    
}
jQuery.fn.dataTableExt.oSort['by-marklink-asc']  = function(x,y) { return mark_marklink(x,y) };
jQuery.fn.dataTableExt.oSort['by-marklink-desc'] = function(x,y) { return mark_marklink(y,x) };

// turn on CourseOffering autocomplete for field with this id.
// adapted from http://www.petefreitag.com/item/756.cfm
// and http://forum.jquery.com/topic/autocomplete-force-selection
function offering_autocomplete(id) {
  $('#' + id).each(function() {
    var autoCompelteElement = this;
    var autoCompelteElementJQ = $(this);
    var formElementName = $(this).attr('name');
    var formElementValue = $(this).attr('value');
    var hiddenElementID  = formElementName + '_autocomplete_hidden';
    /* change name of orig input */
    $(this).attr('name', formElementName + '_autocomplete_label');
    /* create new hidden input with name of orig input */
    $(this).after("<input type=\"hidden\" name=\"" + formElementName + "\" id=\"" + hiddenElementID + "\" value = \"" + formElementValue + "\" />");

    ac = $(this).autocomplete({source:'/data/offerings',
      minLength: 2,
      select: function(event, ui) {
        var selectedObj = ui.item;
        $(autoCompelteElement).val(selectedObj.label);
        $('#'+hiddenElementID).val(selectedObj.value);
        $(this).data("uiLabel", selectedObj.label);
        $(this).data("uiValue", selectedObj.value);
        return false;
      }
    }).bind('blur', function() {
      $(this).val($(this).data("uiLabel"));
        $('#'+hiddenElementID).val($(this).data("uiValue"));
    }).data("uiValue", formElementValue);
    
    /* pre-fill label value if it exists */
    if(formElementValue!=""){
      jQuery.ajax('/data/offering?id=' + formElementValue)
        .done(function(data) {
          autoCompelteElementJQ.val(data);
          ac.data("uiLabel", data);
        });
   }
  });
  
} 

// turn on StudentSearch autocomplete for field with this id.
function student_autocomplete(id) {
  //var regexp = /(,.*)/;
  //var label;
  $('#' + id).each(function() {
    $(this).autocomplete({
      source:'/data/students',
      minLength: 2,
      select: function(event, ui){
        $(this).data("val", ui.item.value);
        //label = ui.item.label.replace(regexp, "")
        //$('#' + id).parent().after("<li>" + label +"</li>");
      }
    }).bind('blur', function(){
      $(this).val($(this).data("val"))
    });
  });
}
