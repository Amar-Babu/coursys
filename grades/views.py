from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models.aggregates import Max
from coredata.models import Member, CourseOffering, Person, Role
from courselib.auth import *
from grades.models import ACTIVITY_STATUS, all_activities_filter, Activity, \
                        NumericActivity, LetterActivity, CalNumericActivity, ACTIVITY_TYPES
from grades.forms import NumericActivityForm, LetterActivityForm, CalNumericActivityForm, \
                         ActivityFormEntry, FormulaFormEntry, FORMTYPE
from grades.models import *
from grades.utils import StudentActivityInfo, reorder_course_activities, create_StudentActivityInfo_list, \
                        ORDER_TYPE, FormulaTesterActivityEntry, FakeActivity
from marking.models import get_group_mark
from groups.models import *
from log.models import LogEntry
from contrib import messages
import pickle
from grades.formulas import parse, activities_dictionary, eval_parse, cols_used, EvalException


FROMPAGE = {'course': 'course', 'activityinfo': 'activityinfo', 'activityinfo_group' : 'activityinfo_group'}

# Only for display purpose.
ACTIVITY_TYPE = {'NG': 'Numeric Graded', 'LG': 'Letter Graded',
                 'CNG': 'Calculated Numeric Graded', 'CLG': 'Calculated Letter Graded'}

@login_required
def course_info(request, course_slug):
    #if course staff
    if is_course_staff_by_slug(request.user, course_slug):
        return _course_info_staff(request, course_slug)
    #else course member
    elif is_course_student_by_slug(request.user, course_slug):
        return _course_info_student(request, course_slug)
    #else not found, return 403
    else:
        return ForbiddenResponse(request)

def _course_info_staff(request, course_slug):
    """
    Course front page
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST':
        id_up = request.POST.get('id_up') 
        id_down = request.POST.get('id_down')
        if id_up == None or id_down == None:                      
            return HttpResponse("Order update failed!")
        # swap the position of the two activities
        activity_up = get_object_or_404(Activity, id=id_up);
        activity_down = get_object_or_404(Activity, id=id_down);
        temp = activity_up.position
        activity_up.position = activity_down.position
        activity_down.position = temp
        activity_up.save()
        activity_down.save()
        return HttpResponse("Order updated!")

    # Todo: is the activity type necessary?
    activities = all_activities_filter(offering=course, deleted=False)
    activities_info = []
    for activity in activities:
        if isinstance(activity, NumericActivity):
            activities_info.append({'activity':activity, 'type':ACTIVITY_TYPE['NG']})            
        elif isinstance(activity, LetterActivity):
            activities_info.append({'activity':activity, 'type':ACTIVITY_TYPE['LG']})
    
    context = {'course': course, 'activities_info': activities_info, 'from_page': FROMPAGE['course'],
               'order_type': ORDER_TYPE}
    return render_to_response("grades/course_info_staff.html", context,
                              context_instance=RequestContext(request))
    

#@requires_course_student_by_slug
def _course_info_student(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course, status__in=['RLS', 'URLS'], deleted=False)
    
    activityinfo_list = []
    for activity in activities:
        activityinfo_list.append(create_StudentActivityInfo_list(course, activity,
                student=Person.objects.get(userid=request.user.username))[0].append_activity_stat())
    context = {'course': course, 'activityinfo_list': activityinfo_list, 'from_page': FROMPAGE['course']}
    return render_to_response("grades/course_info_student.html", context,
                              context_instance=RequestContext(request))

@login_required
def activity_info(request, course_slug, activity_slug):
    if is_course_staff_by_slug(request.user, course_slug):
        return _activity_info_staff(request, course_slug, activity_slug)
    elif is_course_student_by_slug(request.user, course_slug):
        return _activity_info_student(request, course_slug, activity_slug)
    else:
        return ForbiddenResponse(request)

def _activity_info_staff(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)
    
    activity = activities[0]
    # build list of activities with metainfo
    student_grade_info_list = create_StudentActivityInfo_list(course, activity)
    if isinstance(activity, CalNumericActivity):
        activity_type = ACTIVITY_TYPE['CNG']
    elif isinstance(activity, NumericActivity):
        activity_type = ACTIVITY_TYPE['NG']
    elif isinstance(activity, LetterActivity):
        activity_type = ACTIVITY_TYPE['LG']

    context = {'course': course, 'activity_type': activity_type, 'activity': activity, 'student_grade_info_list': student_grade_info_list, 'from_page': FROMPAGE['activityinfo']}
    return render_to_response('grades/activity_info.html', context, context_instance=RequestContext(request))


def _activity_info_student(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    
    if len(activities) != 1:
        return NotFoundResponse(request)

    activity = activities[0]
    if activity.status=="INVI":
        return NotFoundResponse(request)

    # only display summary stats for courses with at least 10 students
    student_count = Member.objects.filter(offering=course, role="STUD").count()
    display_summary = student_count >= 10 and activity.status=="RLS"
    
    activityinfo = create_StudentActivityInfo_list(course, activity, student=Person.objects.get(userid=request.user.username))[0].append_activity_stat()

    context = {'course': course, 'activity': activity, 'activityinfo': activityinfo, 'display_summary': display_summary}
    return render_to_response('grades/activity_info_student.html', context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def activity_info_with_groups(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)
    
    activity = activities[0]
    # build list of group grades information
    all_members = GroupMember.objects.select_related('group', 'student__person').filter(activity = activity, confirmed = True)
    groups_found = {}
    grouped_students = 0
    for member in all_members:
        grouped_students += 1
        group = member.group
        student = member.student.person
        if not groups_found.has_key(group.id):
            # a new group discovered by its first member
            # get the current grade of the group 
            current_mark = get_group_mark(activity, group)
            value = (current_mark == None and 'no grade' or current_mark.mark)
            new_group_grade_info = {'group': group, 'members': [student], 'grade': value}            
            groups_found[group.id] = new_group_grade_info
        else:   
            # add this member to its corresponding group info          
            group_grade_info = groups_found[group.id]
            group_grade_info['members'].append(student)
    
    ungrouped_students = Member.objects.filter(offering = course, role = 'STUD').count() - grouped_students 
    
    if isinstance(activity, NumericActivity):
        activity_type = ACTIVITY_TYPE['NG']
    elif isinstance(activity, LetterActivity):
        activity_type = ACTIVITY_TYPE['LG']

    context = {'course': course, 'activity_type': activity_type, 
               'activity': activity, 'ungrouped_students': ungrouped_students, \
               'group_grade_info_list': groups_found.values(), 'from_page': FROMPAGE['activityinfo_group']}
    return render_to_response('grades/activity_info_with_groups.html', context, context_instance=RequestContext(request))
   
            
@requires_course_staff_by_slug
def activity_info_student(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)
        
    activity = activities[0]
    student = get_object_or_404(Person, userid=userid)
    student_grade_info = create_StudentActivityInfo_list(course, activity, student)[0]
    context = {'course': course, 'activity': activity, 'student_grade_info': student_grade_info}
    return render_to_response('grades/student_grade_info.html', context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def add_numeric_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST': # If the form has been submitted...
        form = NumericActivityForm(request.POST) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                a = NumericActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                max_grade=form.cleaned_data['max_grade'],
                                                offering=course, position=position)
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created a numeric activity %s") % (a),
                      related_object=a)
                l.save()
            except NotImplementedError:
                return NotFoundResponse(request)
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
    else:
        form = NumericActivityForm()
    context = {'course': course, 'form': form, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/numeric_activity_form.html', context, context_instance=RequestContext(request))
    
@requires_course_staff_by_slug
def add_cal_numeric_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    numeric_activities = NumericActivity.objects.filter(offering=course)
    
    if request.method == 'POST': # If the form has been submitted...
        form = CalNumericActivityForm(request.POST) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                CalNumericActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                max_grade=form.cleaned_data['max_grade'],
                                                formula=form.cleaned_data['formula'],
                                                offering=course, position=position)
            except NotImplementedError:
                return NotFoundResponse(request)
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
    else:
        form = CalNumericActivityForm()
    context = {'course': course, 'form': form, 'numeric_activities': numeric_activities, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/cal_numeric_activity_form.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def formula_tester(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    numeric_activities = NumericActivity.objects.filter(offering=course, deleted=False)
    result = ""
    
    if request.method == 'POST': # If the form has been submitted...
        activity_entries = []
        faked_activities = [] # used to evaluate the formula
        has_error = False
        for numeric_activity in numeric_activities:
            activity_form_entry = ActivityFormEntry(request.POST, prefix=numeric_activity.slug)
            if not activity_form_entry.is_valid():
                has_error = True
            else:
                value = activity_form_entry.cleaned_data['value']
                if not value:
                    value = 0
                faked_activities.append(FakeActivity(numeric_activity.name, numeric_activity.short_name,
                                                     activity_form_entry.cleaned_data['status'], value))
            activity_entries.append(FormulaTesterActivityEntry(numeric_activity, activity_form_entry))
            

        formula_form_entry = FormulaFormEntry(request.POST)
        formula_form_entry.activate_form_entry_validation(course_slug)
        
        if not formula_form_entry.is_valid():
            has_error = True
        if has_error:
            messages.error(request, "Please correct the error below")
        else:
            parsed_expr = pickle.loads(formula_form_entry.pickled_formula)
            act_dict = activities_dictionary(faked_activities)
            try:
                result = eval_parse(parsed_expr, act_dict, None)
            except EvalException:
                messages.error(request,  "Can not evaluate formula")
    else:
        activity_entries = []
        for numeric_activity in numeric_activities:
            activity_form_entry = ActivityFormEntry(prefix=numeric_activity.slug)
            activity_entries.append(FormulaTesterActivityEntry(numeric_activity, activity_form_entry))
        formula_form_entry = FormulaFormEntry()
    context = {'course': course, 'activity_entries': activity_entries,
               'formula_form_entry': formula_form_entry, 'result': result}
    return render_to_response('grades/formula_tester.html', context, context_instance=RequestContext(request))

def _create_activity_formdatadict(activity):
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        return
    data = dict()
    data['name'] = activity.name
    data['short_name'] = activity.short_name
    data['status'] = activity.status
    data['due_date'] = activity.due_date
    data['percent'] = activity.percent
    data['position'] = activity.position
    if hasattr(activity, 'max_grade'):
        data['max_grade'] = activity.max_grade
    if hasattr(activity, 'formula'):
        data['formula'] = activity.formula
    return data

def _populate_activity_from_formdata(activity, data):
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        return
    if data.has_key('name'):
        activity.name = data['name']
    if data.has_key('short_name'):
        activity.short_name = data['short_name']
    if data.has_key('status'):
        activity.status = data['status']
    if data.has_key('due_date'):
        activity.due_date = data['due_date']
    if data.has_key('percent'):
        activity.percent = data['percent']
    if data.has_key('max_grade'):
        activity.max_grade = data['max_grade']
    if data.has_key('formula'):
        activity.formula = data['formula']

@requires_course_staff_by_slug
def edit_activity(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if (len(activities) == 1):
        activity = activities[0]
                
        from_page = request.GET.get('from_page')
        if from_page == None:
            from_page = FROMPAGE['course']
        
        if request.method == 'POST': # If the form has been submitted...
            if isinstance(activity, CalNumericActivity):
                form = CalNumericActivityForm(request.POST) # A form bound to the POST data
                form.activate_editform_validation(course_slug, activity_slug)
            elif isinstance(activity, NumericActivity):
                form = NumericActivityForm(request.POST) # A form bound to the POST data
                form.activate_editform_validation(course_slug, activity_slug)
            elif isinstance(activity, LetterActivity):
                form = LetterActivityForm(request.POST) # A form bound to the POST data
                form.activate_editform_validation(course_slug, activity_slug)
            if form.is_valid(): # All validation rules pass
                _populate_activity_from_formdata(activity, form.cleaned_data)
                activity.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("edited %s") % (activity),
                      related_object=activity)
                l.save()
                #print from_page
                if from_page == FROMPAGE['course']:
                    return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
                elif from_page == FROMPAGE['activityinfo']:
                    return HttpResponseRedirect(reverse('grades.views.activity_info',
                                                        kwargs={'course_slug': course_slug, 'activity_slug': activity_slug}))
        else:
            datadict = _create_activity_formdatadict(activity)
            if isinstance(activity, CalNumericActivity):
                form = CalNumericActivityForm(datadict)
            elif isinstance(activity, NumericActivity):
                form = NumericActivityForm(datadict)
            elif isinstance(activity, LetterActivity):
                form = LetterActivityForm(datadict)
        
        if isinstance(activity, CalNumericActivity):
            numeric_activities = NumericActivity.objects.exclude(slug=activity_slug).filter(offering=course)
            context = {'course': course, 'activity': activity, 'form': form, 'numeric_activities': numeric_activities,
                       'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/cal_numeric_activity_form.html', context, context_instance=RequestContext(request))
        elif isinstance(activity, NumericActivity):
            context = {'course': course, 'activity': activity, 'form': form, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/numeric_activity_form.html', context, context_instance=RequestContext(request))
        elif isinstance(activity, LetterActivity):
            context = {'course': course, 'activity': activity, 'form': form, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/letter_activity_form.html', context, context_instance=RequestContext(request))
        
    else:
        return NotFoundResponse(request)
    

    
@requires_course_staff_by_slug
def add_letter_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST': # If the form has been submitted...
        form = LetterActivityForm(request.POST) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            #try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                a = LetterActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                offering=course, position=position)
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created a letter-graded activity %s") % (a),
                      related_object=a)
                l.save()
            #except Exception:
            #    raise Http404
                return HttpResponseRedirect(reverse('grades.views.course_info',
                                                kwargs={'course_slug': course_slug}))
    else:
        form = LetterActivityForm()
    activities = course.activity_set.all()
    context = {'course': course, 'form': form, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/letter_activity_form.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def delete_activity_review(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course, slug=activity_slug)
    if (len(activities) == 1):
        activity = activities[0]
        if isinstance(activity, CalNumericActivity):
            activity_type = ACTIVITY_TYPE['CNG']
        elif isinstance(activity, NumericActivity):
            activity_type = ACTIVITY_TYPE['NG']
        elif isinstance(activity, LetterActivity):
            activity_type = ACTIVITY_TYPE['LG']
        context = {'course': course, 'activity_type': activity_type, 'activity': activities[0]}
        return render_to_response('grades/delete_activity_review.html', context, context_instance=RequestContext(request))
    else:
        return NotFoundResponse(request)

@requires_course_staff_by_slug
def delete_activity_confirm(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, offering=course, slug=activity_slug)
    activity.deleted = True
    activity.save()
    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
          description=("deleted %s") % (activity),
          related_object=activity)
    l.save()
    return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))

@requires_course_staff_by_slug
def all_grades(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)
    students = Member.objects.filter(offering=course, role="STUD").select_related('person')
    
    # get grade data into a format we can work with
    grades = {}
    for a in activities:
        grades[a.slug] = {}
        if hasattr(a, 'numericgrade_set'):
            gs = a.numericgrade_set.all()
        else:
            gs = a.lettergrade_set.all()
        for g in gs:
            grades[a.slug][g.member.person.userid] = g
    
    #print grades
    context = {'course': course, 'students': students, 'activities': activities, 'grades': grades}
    return render_to_response('grades/all_grades.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def student_info(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, person__userid=userid, offering__slug=course_slug)
    activities = all_activities_filter(offering=course)
    
    if member.role != "STUD":
        return NotFoundResponse(request)
    
    grades = {}
    for a in activities:
        if hasattr(a, 'numericgrade_set'):
            gs = a.numericgrade_set.filter(member=member)
        else:
            gs = a.lettergrade_set.filter(member=member)

        if gs:
            grades[a.slug] = {userid: gs[0]}
        else:
            grades[a.slug] = {}

    
    context = {'course': course, 'member': member, 'activities': activities, 'grades': grades}
    return render_to_response('grades/student_info.html', context, context_instance=RequestContext(request))







