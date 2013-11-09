from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from coredata.forms import RoleForm, UnitRoleForm, InstrRoleFormSet, MemberForm, PersonForm, TAForm, \
        UnitAddressForm, UnitForm, SemesterForm, SemesterWeekFormset, HolidayFormset, SysAdminSearchForm
from courselib.auth import requires_global_role, requires_role, requires_course_staff_by_slug, ForbiddenResponse, \
        has_formgroup
from courselib.search import get_query, find_userid_or_emplid
from coredata.models import Person, Semester, CourseOffering, Course, Member, Role, Unit, SemesterWeek, Holiday, \
        UNIT_ROLES, ROLES, ROLE_DESCR, INSTR_ROLES
from advisornotes.models import NonStudent
from log.models import LogEntry
from django.core.urlresolvers import reverse
from django.contrib import messages
import json, datetime

@requires_global_role("SYSA")
def sysadmin(request):
    if 'usersearch' in request.GET:
        # user search
        form = SysAdminSearchForm(request.GET)
        if form.is_valid() and form.cleaned_data['user']:
            emplid = form.cleaned_data['user'].emplid
            return HttpResponseRedirect(reverse(user_summary, kwargs={'userid': emplid}))
    elif 'offeringsearch' in request.GET:
        # course offering search
        form = SysAdminSearchForm(request.GET)
        if form.is_valid() and form.cleaned_data['offering']:
            offering = form.cleaned_data['offering']
            return HttpResponseRedirect(reverse(offering_summary, kwargs={'course_slug': offering.slug}))
    else:
        form = SysAdminSearchForm()
    
    return render(request, 'coredata/sysadmin.html', {'form': form})

@requires_global_role("SYSA")
def role_list(request):
    """
    Display list of who has what role
    """
    roles = Role.objects.exclude(role="NONE")
    
    return render(request, 'coredata/roles.html', {'roles': roles})

@requires_global_role("SYSA")
def new_role(request, role=None):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Added role %s for %s.' % (form.instance.get_role_display(), form.instance.person.name()))
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new role: %s as %s") % (form.instance.person.userid, form.instance.role),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse(role_list))
    else:
        form = RoleForm()

    return render(request, 'coredata/new_role.html', {'form': form})

@requires_global_role("SYSA")
def delete_role(request, role_id):
    role = get_object_or_404(Role, pk=role_id)
    messages.success(request, 'Deleted role %s for %s.' % (role.get_role_display(), role.person.name()))
    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
          description=("deleted role: %s for %s") % (role.get_role_display(), role.person.name()),
          related_object=role.person)
    l.save()
    
    role.delete()
    return HttpResponseRedirect(reverse(role_list))



@requires_global_role("SYSA")
def unit_list(request):
    """
    Display list of all units
    """
    units = Unit.objects.all()
    return render(request, 'coredata/units.html', {'units': units})

@requires_global_role("SYSA")
def edit_unit(request, unit_slug=None):
    if unit_slug:
        unit = get_object_or_404(Unit, slug=unit_slug)
    else:
        unit = Unit()
    
    if request.method == 'POST':
        form = UnitForm(instance=unit, data=request.POST)
        if form.is_valid():
            unit.slug = None
            form.save()
            messages.success(request, 'Edited unit %s.' % (unit.name))
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited unit %s") % (form.instance.slug),
                  related_object=unit)
            l.save()
            return HttpResponseRedirect(reverse(unit_list))
    else:
        form = UnitForm(instance=unit)
    
    context = {'form': form}
    return render(request, 'coredata/edit_unit.html', context)





@requires_global_role("SYSA")
def members_list(request):
    members = Member.objects.exclude(added_reason="AUTO").exclude(added_reason="CTA")
    return render(request, 'coredata/members_list.html', {'members': members})


@requires_global_role("SYSA")
def edit_member(request, member_id=None):
    if member_id:
        member = get_object_or_404(Member, id=member_id)
    else:
        member = None

    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited membership: %s as %s in %s") % (form.instance.person.userid, form.instance.role, form.instance.offering),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse(members_list))
    elif member_id:
        form = MemberForm(instance=member, initial={'person': member.person.userid})
    else:
        form = MemberForm()
    
    return render(request, 'coredata/edit_member.html', {'form': form, 'member': member})


@requires_global_role("SYSA")
def user_summary(request, userid):
    query = find_userid_or_emplid(userid)
    user = get_object_or_404(Person, query)
    
    memberships = Member.objects.filter(person=user)
    roles = Role.objects.filter(person=user).exclude(role="NONE")
    
    context = {'user': user, 'memberships': memberships, 'roles': roles}
    return render(request, "coredata/user_summary.html", context)

@requires_global_role("SYSA")
def offering_summary(request, course_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    
    staff = Member.objects.filter(offering=offering, role__in=['INST', 'TA'])
    
    context = {'offering': offering, 'staff': staff}
    return render(request, "coredata/offering_summary.html", context)


@requires_global_role("SYSA")
def new_person(request):
    if request.method == 'POST':
        form = PersonForm(request.POST)
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new person added: %s (%s)") % (form.instance.name(), form.instance.userid),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse(sysadmin))
    else:
        form = PersonForm()

    return render(request, 'coredata/new_person.html', {'form': form})


# semester object management

@requires_global_role("SYSA")
def semester_list(request):
    semesters = Semester.objects.all()
    return render(request, 'coredata/semester_list.html', {'semesters': semesters})

@requires_global_role("SYSA")
def edit_semester(request, semester_name=None):
    if semester_name:
        semester = get_object_or_404(Semester, name=semester_name)
        newsem = False
    else:
        semester = Semester()
        newsem = True
    
    if request.method == 'POST':
        form = SemesterForm(instance=semester, prefix='sem', data=request.POST)
        week_formset = SemesterWeekFormset(queryset=SemesterWeek.objects.filter(semester=semester), prefix='week', data=request.POST)
        holiday_formset = HolidayFormset(queryset=Holiday.objects.filter(semester=semester), prefix='holiday', data=request.POST)
        if form.is_valid() and week_formset.is_valid() and holiday_formset.is_valid():
            sem = form.save()
            
            weeks = week_formset.save(commit=False)
            for week in weeks:
                week.semester = sem
                week.save()

            holidays = holiday_formset.save(commit=False)
            for holiday in holidays:
                holiday.semester = sem
                holiday.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited semester %s") % (sem.name),
                  related_object=sem)
            l.save()
            messages.success(request, 'Edited semester %s.' % (sem.name))
            return HttpResponseRedirect(reverse('coredata.views.semester_list', kwargs={}))
    else:
        form = SemesterForm(instance=semester, prefix='sem')
        week_formset = SemesterWeekFormset(queryset=SemesterWeek.objects.filter(semester=semester), prefix='week')
        holiday_formset = HolidayFormset(queryset=Holiday.objects.filter(semester=semester), prefix='holiday')

    context = {'semester': semester, 'form': form, 'newsem': newsem,
               'week_formset': week_formset, 'holiday_formset': holiday_formset}
    return render(request, 'coredata/edit_semester.html', context)


# views to let instructors manage TAs

@requires_course_staff_by_slug
def manage_tas(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    longform = False
    if not Member.objects.filter(offering=course, person__userid=request.user.username, role="INST"):
        # only instructors can manage TAs
        return ForbiddenResponse(request, "Only instructors can manage TAs")
    
    if request.method == 'POST' and 'action' in request.POST and request.POST['action']=='add':
        form = TAForm(offering=course, data=request.POST)
        if form.non_field_errors():
            # have an unknown userid
            longform = True
        elif form.is_valid():
            userid = form.cleaned_data['userid']
            if not Person.objects.filter(userid=userid) \
                    and form.cleaned_data['fname'] and form.cleaned_data['lname']:
                # adding a new person: handle that.
                eid = 1
                # search for an unused temp emplid
                while True:
                    emplid = "%09i" % (eid)
                    if not Person.objects.filter(emplid=emplid):
                        break
                    eid += 1
                p = Person(first_name=form.cleaned_data['fname'], pref_first_name=form.cleaned_data['fname'], last_name=form.cleaned_data['lname'], middle_name='', userid=userid, emplid=emplid)
                p.save()

            else:
                p = Person.objects.get(userid=userid)

            m = Member(person=p, offering=course, role="TA", credits=0, career="NONS", added_reason="TAIN")
            m.save()
                
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("TA added by instructor: %s for %s") % (userid, course),
                  related_object=m)
            l.save()
            messages.success(request, 'Added %s as a TA.' % (p.name()))
            return HttpResponseRedirect(reverse(manage_tas, kwargs={'course_slug': course.slug}))
            

    elif request.method == 'POST' and 'action' in request.POST and request.POST['action']=='del':
        userid = request.POST['userid']
        ms = Member.objects.filter(person__userid=userid, offering=course, role="TA", added_reason="TAIN")
        if ms:
            m = ms[0]
            m.role = "DROP"
            m.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("TA removed by instructor: %s for %s") % (userid, course),
                  related_object=m)
            l.save()
            messages.success(request, 'Removed %s as a TA.' % (m.person.name()))
        return HttpResponseRedirect(reverse(manage_tas, kwargs={'course_slug': course.slug}))

    else:
        form = TAForm(offering=course)

    tas = Member.objects.filter(role="TA", offering=course)
    context = {'course': course, 'form': form, 'tas': tas, 'longform': longform}
    return render(request, 'coredata/manage_tas.html', context)


# views for departmental admins to manage permissions

@requires_role("ADMN")
def unit_admin(request):
    """
    Unit admin front page
    """
    return render(request, 'coredata/unit_admin.html', {'units': request.units})

@requires_role("ADMN")
def unit_role_list(request):
    """
    Display list of who has what role (for department admins)
    """
    roles = Role.objects.filter(unit__in=request.units, role__in=UNIT_ROLES)
    return render(request, 'coredata/unit_roles.html', {'roles': roles})

@requires_role("ADMN")
def new_unit_role(request, role=None):
    role_choices = [(r,ROLES[r]) for r in UNIT_ROLES]
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    if request.method == 'POST':
        form = UnitRoleForm(request.POST)
        form.fields['role'].choices = role_choices
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new role: %s as %s in %s") % (form.instance.person.userid, form.instance.role, form.instance.unit),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse(unit_role_list))
    else:
        form = UnitRoleForm()
        form.fields['role'].choices = role_choices
        form.fields['unit'].choices = unit_choices
        
    context = {'form': form, 'UNIT_ROLES': UNIT_ROLES, 'ROLE_DESCR': ROLE_DESCR}
    return render(request, 'coredata/new_unit_role.html', context)


@requires_role("ADMN")
def delete_unit_role(request, role_id):
    role = get_object_or_404(Role, pk=role_id, unit__in=request.units, role__in=UNIT_ROLES)
    messages.success(request, 'Deleted role %s for %s.' % (role.get_role_display(), role.person.name()))
    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
          description=("deleted role: %s for %s in %s") % (role.get_role_display(), role.person.name(), role.unit),
          related_object=role.person)
    l.save()
    
    role.delete()
    return HttpResponseRedirect(reverse(unit_role_list))


@requires_role('ADMN')
def unit_address(request, unit_slug):
    unit = get_object_or_404(Unit, slug=unit_slug)
    if unit not in request.units:
        return ForbiddenResponse(request, "Not an admin for this unit")
    
    if request.method == 'POST':
        form = UnitAddressForm(data=request.POST, unit=unit)
        if form.is_valid():
            #print form.cleaned_data
            form.copy_to_unit()
            unit.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("updated contact info for %s") % (unit.label),
                  related_object=unit)
            l.save()
            return HttpResponseRedirect(reverse('coredata.views.unit_admin'))
    else:
        form = UnitAddressForm(unit=unit)
    context = {'unit': unit, 'form': form}
    return render(request, "coredata/unit_address.html", context)


@requires_role('ADMN')
def missing_instructors(request, unit_slug):
    unit = get_object_or_404(Unit, slug=unit_slug)
    if unit not in request.units:
        return ForbiddenResponse(request, "Not an admin for this unit")

    # build a set of all instructors that don't have an instructor-appropriate role
    roles = dict(((r.person, r.role) for r in Role.objects.filter(unit=unit, role__in=INSTR_ROLES).select_related('person')))
    missing = set()
    long_ago = datetime.date.today() - datetime.timedelta(days=365*3)
    instructors = Member.objects.filter(role="INST", offering__owner=unit,
                                        offering__semester__start__gte=long_ago) \
                                .exclude(offering__component='CAN') \
                                .exclude(person__userid=None) \
                                .select_related('person')
    for i in instructors:
        if i.person not in roles:
            missing.add(i.person)
    missing = list(missing)
    missing.sort()
    initial = [{'person': p, 'role': None} for p in missing]

    if request.method == 'POST':
        formset = InstrRoleFormSet(request.POST, initial=initial)
        if formset.is_valid():
            count = 0
            for f in formset.forms:
                p = f.cleaned_data['person']
                r = f.cleaned_data['role']
                if r == "NONE" or p not in missing:
                    continue
                
                r = Role(person=p, role=r, unit=unit)
                r.save()
                count += 1

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("new role: %s as %s") % (p.userid, r),
                      related_object=r)
                l.save()
            messages.success(request, 'Set instructor roles for %i people.' % (count))
            return HttpResponseRedirect(reverse('coredata.views.unit_admin'))
    else:
        formset = InstrRoleFormSet(initial=initial)

    context = {'formset': formset, 'unit': unit}
    return render(request, 'coredata/missing_instructors.html', context)





# AJAX/JSON for course offering selector autocomplete
def offerings_search(request):
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")
    term = request.GET['term']
    response = HttpResponse(mimetype='application/json')
    data = []
    query = get_query(term, ['subject', 'number', 'section', 'semester__name', 'title'])
    offerings = CourseOffering.objects.filter(query).exclude(component="CAN").select_related('semester')
    for o in offerings:
        label = o.search_label_value()
        d = {'value': o.id, 'label': label}
        data.append(d)
    json.dump(data, response, indent=1)
    return response

# AJAX/JSON for course selector autocomplete
def course_search(request):
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")
    term = request.GET['term']
    response = HttpResponse(mimetype='application/json')
    data = []
    query = get_query(term, ['subject', 'number', 'title'])
    courses = Course.objects.filter(query)
    for c in courses:
        label = "%s %s" % (c.subject, c.number)
        d = {'value': c.id, 'label': label}
        data.append(d)
    json.dump(data, response, indent=1)
    return response

# AJAX/JSON for student search autocomplete
@login_required
def student_search(request):
    # check permissions
    roles = Role.all_roles(request.user.username)
    allowed = set(['ADVS', 'ADMN', 'GRAD', 'FUND', 'SYSA'])
    if not(roles & allowed):
        # doesn't have any allowed roles
        if not has_formgroup(request):
            return ForbiddenResponse(request, "Not permitted to do student search.")
    
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")
    term = request.GET['term']
    response = HttpResponse(mimetype='application/json')

    studentQuery = get_query(term, ['userid', 'emplid', 'first_name', 'last_name'])
    students = Person.objects.filter(studentQuery)[:100]

    if 'nonstudent' in request.GET and 'ADVS' in roles:
        nonStudentQuery = get_query(term, ['first_name', 'last_name', 'pref_first_name'])
        nonStudents = NonStudent.objects.filter(nonStudentQuery)[:100]
    else:
        nonStudents = []

    data = [{'value': s.emplid, 'label': s.search_label_value()} for s in students]
    data.extend([{'value': n.slug, 'label': n.search_label_value()} for n in nonStudents])

    data.sort(key = lambda x: x['label'])

    json.dump(data, response, indent=1)
    return response

def offering_by_id(request):
    if 'id' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'id' query.")
    id_ = request.GET['id']
    try:
        int(id_)
    except ValueError:
        return ForbiddenResponse(request, "'id' must be an integer.")

    offering = get_object_or_404(CourseOffering, pk=id_)
    return HttpResponse(offering.search_label_value())


from coredata.queries import find_person
@login_required
def XXX_sims_person_search(request):
    # check permissions
    roles = Role.all_roles(request.user.username)
    allowed = set(['ADVS', 'ADMN', 'GRAD', 'FUND'])
    if not(roles & allowed):
        # doesn't have any allowed roles
        return ForbiddenResponse(request, "Not permitted to do person search.")
    
    if 'emplid' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'emplid' query.")
    emplid = request.GET['emplid']
    response = HttpResponse(mimetype='application/json')

    data = find_person(emplid)
    
    json.dump(data, response, indent=1)
    return response











from django import forms
from coredata.models import CAMPUS_CHOICES
class OfferingFilterForm(forms.Form):
    subject = forms.ChoiceField()
    section = forms.CharField(widget=forms.TextInput(attrs={'size': '4'}))
    instructor = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), label='Instructor Userid')
    campus = forms.ChoiceField(choices=([('', u'all')] + list(CAMPUS_CHOICES)))
    semester = forms.ChoiceField()
    crstitle = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), label='Title Contains')
    
    def __init__(self, *args, **kwargs):
        super(OfferingFilterForm, self).__init__(*args, **kwargs)
        # subject choices: all that exist in the DB
        subjects = Course.objects.order_by().values_list('subject', flat=True).distinct()
        self.fields['subject'].choices = [('', u'all')] + [(s,s) for s in subjects]
        # semester choices: two years either-side of today
        today = datetime.date.today()
        semesters = Semester.objects.filter(start__lte=today+datetime.timedelta(days=730), end__gte=today-datetime.timedelta(days=730)).order_by('-name')
        self.fields['semester'].choices = [('', u'all')] + [(s.name, s.label()) for s in semesters]


def browse_courses(request):
    if 'tabledata' in request.GET:
        # table data
        return _offering_data(request)
    if 'instructor_autocomplete' in request.GET:
        # instructor autocomplete search
        return _instructor_autocomplete(request)

    # actually displaying the page at this point
    form = OfferingFilterForm()
    context = {
        'form': form,
        }
    return render(request, 'coredata/browse_courses.html', context)



from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q

class OfferingDataJson(BaseDatatableView):
    model = CourseOffering
    columns = ['semester', 'coursecode', 'section', 'title', 'instructors', 'enrl_tot']
    order_columns = ['semester__name', ['subject', 'number'], 'section', 'title', [], 'enrl_tot']
    max_display_length = 500

    def render_column(self, offering, column):
        if column == 'coursecode':
            return '%s %s' % (offering.subject, offering.number)
        elif column == 'instructors':
            return offering.instructors_str()
        elif hasattr(offering, 'get_%s_display' % column):
            # it's a choice field
            return getattr(offering, 'get_%s_display' % column)()
        else:
            return unicode(getattr(offering, column))

    def ordering(self, qs):
        return super(OfferingDataJson, self).ordering(qs)

    def filter_queryset(self, qs):
        # use request parameters to filter queryset
        GET = self.request.GET
        
        qs = qs.exclude(component='CAN')

        srch = GET.get('sSearch', None)
        if srch:
            qs = qs.filter(Q(title__istartswith=srch) | Q(number__istartswith=srch)) 

        subject = GET.get('subject', None)
        if subject:
            qs = qs.filter(subject=subject)
            
        section = GET.get('section', None)
        if section:
            qs = qs.filter(section__startswith=section)

        instructor = GET.get('instructor', None)
        if instructor:
            off_ids = Member.objects.order_by().filter(person__userid=instructor, role='INST').values_list('offering', flat=True)[:500]
            qs = qs.filter(id__in=off_ids)
            
        campus = GET.get('campus', None)
        if campus:
            qs = qs.filter(campus=campus)

        semester = GET.get('semester', None)
        if semester:
            qs = qs.filter(semester__name=semester)

        title = GET.get('crstitle', None)
        if title:
            qs = qs.filter(title__icontains=title)

        print qs.query
        return qs

_offering_data = OfferingDataJson.as_view()

def _instructor_autocomplete(request):
    """
    Responses for the jQuery autocomplete for instructor search
    """
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")

    response = HttpResponse(mimetype='application/json')
    query = get_query(request.GET['term'], ['person__first_name', 'person__last_name', 'person__userid', 'person__middle_name'])
    # matching person.id values who have actually taught a course
    person_ids = Member.objects.filter(query).filter(role='INST').order_by().values_list('person', flat=True).distinct()[:100]
    # get the Person objects: is there no way to do this in one query?
    people = Person.objects.filter(id__in=person_ids)
    data = [{'value': p.userid, 'label': p.name()} for p in people]
    json.dump(data, response, indent=1)
    return response
