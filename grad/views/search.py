from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradStudent, GradProgram, SavedSearch, GradRequirement, ScholarshipType, \
    STATUS_ACTIVE, STATUS_OBSOLETE, STATUS_CHOICES
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.safestring import mark_safe
from django.contrib import messages
from grad.forms import SearchForm, SaveSearchForm, COLUMN_CHOICES, COLUMN_WIDTHS
from django.core.urlresolvers import reverse
from coredata.models import Person
import unicodecsv as csv
import copy, datetime, json
from grad.templatetags.getattribute import getattribute

MAX_RESULTS = 1000

def _get_cleaned_get(request):
    """
        Returns a GET request with every parameter that has no values removed. 
    """
    cleaned_get = copy.copy(request.GET)
    for parameter, parameter_values in request.GET.iterlists():
        if len(filter(lambda x:len(x) > 0, parameter_values)) == 0:
            del cleaned_get[parameter]
    return cleaned_get

def _parse_sort(sortstr):
    """
    Decode the microformat for search order in URL.
    
    The format is "2a,15d" maps to datables aaSorting value [[2,'asc'], [15,'desc']]
    """
    res = []
    for col in sortstr.split(','):
        if not col:
            return None
        num = col[:-1]
        order = col[-1]
        try:
            num = int(num)
        except ValueError:
            return None
        if order == 'd':
            order = 'desc'
        elif order == 'a':
            order = 'asc'
        else:
            return None
        res.append([num, order])
    return mark_safe(json.dumps(res))

@requires_role("GRAD", get_only=["GRPD"])
def search(request):
    current_user = Person.objects.get(userid=request.user.username)
    query_string = request.META.get('QUERY_STRING','')
    savedsearches = SavedSearch.objects.filter(person=current_user, query=query_string)
    if savedsearches:
        savedsearch = savedsearches[0]
    else:
        savedsearch = None

    #if savedsearch is None:
    #    if len(request.GET) > 0:
    #        cleaned_get = _get_cleaned_get(request)
    #        if len(cleaned_get) < len(request.GET):
    #            return HttpResponseRedirect(reverse(search) + u'?' + cleaned_get.urlencode())
    #    try:
    #        savedsearch = SavedSearch.objects.get(person=current_user, query=query_string)
    #    except SavedSearch.DoesNotExist:
    #        savedsearch = None
    
    form = SearchForm(initial={'student_status': STATUS_ACTIVE}) if len(request.GET) == 0 else SearchForm(request.GET)
    requirement_choices = [(r['series'], r['description']) for r in
            GradRequirement.objects.filter(program__unit__in=request.units, hidden=False)
            .order_by('description').values('series', 'description').distinct()]
    scholarshiptype_choices = [(st.id, st.name) for st in ScholarshipType.objects.filter(unit__in=request.units, hidden=False)]
    program_choices = [(gp.id, gp.label) for gp in GradProgram.objects.filter(unit__in=request.units, hidden=False)]
    status_choices = [(st,desc) for st,desc in STATUS_CHOICES if st not in STATUS_OBSOLETE]
    form.fields['requirements'].choices = requirement_choices
    form.fields['incomplete_requirements'].choices = requirement_choices
    form.fields['scholarshiptype'].choices = scholarshiptype_choices
    form.fields['program'].choices = program_choices
    form.fields['student_status'].choices = status_choices
    
    if 'sort' in request.GET:
        sort = _parse_sort(request.GET['sort'])
    else:
        sort = None;
    
    if 'edit_search' not in request.GET and form.is_valid():
        query = form.get_query()
        #print query
        grads = GradStudent.objects.filter(program__unit__in=request.units).filter(query).select_related('person', 'program').distinct()
        grads = filter(form.secondary_filter(), grads)
        
        overflow = False
        if len(grads) > MAX_RESULTS:
            grads = grads[:MAX_RESULTS]
            overflow = True
        
        if savedsearch is not None:
            saveform = SaveSearchForm(instance=savedsearch)
        else:
            saveform = SaveSearchForm(initial={'person':current_user, 'query':query_string})
        
        columns = form.cleaned_data['columns']
        # Here, we're using a nested list comprehension to convert column ids into column names - 
        #  for example 'person.first_name' into 'First Name' - using the COLUMN_CHOICES table provided in forms.py
        human_readable_column_headers = [[v[1] for _,v in enumerate(COLUMN_CHOICES) if v[0] == column][0] for column in columns]
        
        if 'csv' in request.GET:
            # CSV output
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'inline; filename=grad_search.csv'
            writer = csv.writer(response) 
            
            writer.writerow( human_readable_column_headers )
            
            for grad in grads:
                row = []
                for column in columns:
                    value = getattribute(grad, column, html=False)
                    row.append(value)
                writer.writerow( row )
            return response
        
        elif 'excel' in request.GET:
            # Excel output
            import xlwt
            response = HttpResponse(mimetype='application/vnd.ms-excel')
            response['Content-Disposition'] = 'inline; filename=grad_search.xls'
            
            book = xlwt.Workbook(encoding='utf-8')
            sheet = book.add_sheet('Search Results')
            hdrstyle = xlwt.easyxf('font: bold on; pattern: pattern solid, fore_colour grey25; align: horiz centre')
            evenstyle = xlwt.easyxf('pattern: back_colour gray40')
            oddstyle = xlwt.easyxf('pattern: pattern sparse_dots, fore_colour grey25')
            
            # header row
            sheet.write(0, 0, u'Graduate Student Search Results', xlwt.easyxf('font: bold on, height 320'))
            sheet.row(0).height = 400
            for i,hdr in enumerate(human_readable_column_headers):
                sheet.write(1, i, hdr, hdrstyle)
            
            # data rows
            for i,grad in enumerate(grads):
                style = [oddstyle, evenstyle][i%2]
                for j,column in enumerate(columns):
                    sheet.write(i+2, j, getattribute(grad, column, html=False), style)
            
            # set column widths
            for i,c in enumerate(columns):
                wid = COLUMN_WIDTHS[c]
                sheet.col(i).width = wid
            
            count = len(grads)
            sheet.write(count+4, 0, 'Number of students: %i' % (count))
            sheet.write(count+5, 0, 'Report generated: %s' % (datetime.datetime.now()))
            
            book.save(response)
            return response
        
        if overflow:
            messages.warning(request, "Too many result found: limited to %i." % (MAX_RESULTS))
        context = {
                   'grads': grads,
                   'human_readable_column_headers': human_readable_column_headers,
                   'columns': columns,
                   'saveform' : saveform,
                   'query_string': query_string,
                   'sort': sort,
                   }
        resp = render(request, 'grad/search_results.html', context)
        return resp
    else:
        #savedsearches = SavedSearch.objects.filter(person__in=(current_user,None))
        page_title = 'Graduate Student Advanced Search'
        context = {
                   #'savedsearches' : savedsearches,
                   'page_title' : page_title,
                   'form':form,
                   'savedsearch' : savedsearch,
                   # a non-None savedsearch here means that somehow, an invalid search got saved
                   # the template gives the user the option to delete it
                   }
        resp = render(request, 'grad/search.html', context)
        return resp
