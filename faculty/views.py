from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from courselib.search import find_userid_or_emplid

from coredata.models import Person, Unit, Role, Member, CourseOffering
from grad.models import Supervisor
from ra.models import RAAppointment

from faculty.models import CareerEvent, MemoTemplate
from faculty.forms import career_event_factory
from faculty.forms import CareerEventForm, MemoTemplateForm


def _get_faculty_or_404(allowed_units, userid_or_emplid):
    """
    Get the Person who has Role[role=~"faculty"] if we're allowed to see it, or raise Http404.
    """
    sub_unit_ids = Unit.sub_unit_ids(allowed_units)
    person = get_object_or_404(Person, find_userid_or_emplid(userid_or_emplid))
    roles = get_list_or_404(Role, role='FAC', unit__id__in=sub_unit_ids, person=person)
    units = set(r.unit for r in roles)
    return person, units


###############################################################################
# Top-level views (management, etc. Not specific to a faculty member)

@requires_role('ADMN')
def index(request):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person', 'unit')

    context = {
        'fac_roles': fac_roles,
    }
    return render(request, 'faculty/index.html', context)



###############################################################################
# Display/summary views for a faculty member

@requires_role('ADMN')
def summary(request, userid):
    """
    Summary page for a faculty member.
    """
    person, _ = _get_faculty_or_404(request.units, userid)
    context = {
        'person': person,
    }
    return render(request, 'faculty/summary.html', context)

@requires_role('ADMN')
def events_list(request, userid):
    """
    Display all career events
    """
    person, _ = _get_faculty_or_404(request.units, userid)

    context = {
        'person': person,
    }
    return render(request, 'faculty/career_events_list.html', context)

@requires_role('ADMN')
def otherinfo(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    # TODO: should some or all of these be limited by request.units?

    # collect teaching history
    instructed = Member.objects.filter(role='INST', person=person, added_reason='AUTO') \
            .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
            .select_related('offering', 'offering__semester')

    # collect grad students
    supervised = Supervisor.objects.filter(supervisor=person, supervisor_type__in=['SEN','COS','COM'], removed=False) \
            .select_related('student', 'student__person', 'student__program', 'student__start_semester', 'student__end_semester')


    # RA appointments supervised
    ras = RAAppointment.objects.filter(deleted=False, hiring_faculty=person) \
            .select_related('person', 'project', 'account')

    context = {
        'person': person,
        'instructed': instructed,
        'supervised': supervised,
        'ras': ras,
    }
    return render(request, 'faculty/otherinfo.html', context)



###############################################################################
# Creation and editing of CareerEvents

@requires_role('ADMN')
def create_event(request, userid):
    """
    Create new career event for a faculty member.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    context = {"person": person}
    editor = get_object_or_404(Person, userid=request.user.username)
    unit_choices = [(u.id, unicode(u)) for u in member_units & request.units]
    if request.method == "POST":
        form = CareerEventForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            event = form.save(commit=False)
            event.person = person
            event.save(editor)
            return HttpResponseRedirect(event.get_change_url())
        else:
            context.update({"event_form": form})
    else:
        form = CareerEventForm(initial={"person": person, "status": "NA"})
        form.fields['unit'].choices = unit_choices
        # TODO filter choice for status (some roles may not be allowed to approve events?
        context.update({"event_form": form})
    return render(request, 'faculty/career_event_form.html', context)


@requires_role('ADMN')
def change_event(request, userid, event_slug):
    """
    Change existing career event for a faculty member.
    """
    person, _ = _get_faculty_or_404(request.units, userid)
    instance = get_object_or_404(CareerEvent, slug=event_slug, person=person)
    context = {"person": person, "event": instance}
    editor = get_object_or_404(Person, userid=request.user.username)
    if request.method == "POST":
        form = CareerEventForm(request.POST, instance=instance)
        if form.is_valid():
            event = form.save(commit=False)
            event.save(editor)
            context.update({"event": event,
                            "event_form": form})
    else:
        unit_choices = [(u.id, unicode(u)) for u in request.units]
        form = CareerEventForm(instance=instance)
        form.fields['unit'].choices = unit_choices
        # TODO filter choice for status (as above)
        context.update({"event_form": form})
    return render(request, 'faculty/career_event_form.html', context)


###############################################################################
# Management of DocumentAttachments and Memos

###############################################################################
# Creating and editing Memo Templates

@requires_role('ADMN')
def memo_templates(request):
    templates = MemoTemplate.objects.filter(unit__in=request.units, hidden=False)

    page_title = 'Memo Templates'
    crumb = 'Memo Templates'    
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'templates': templates,          
               }
    return render(request, 'faculty/memo_templates.html', context)

@requires_role('ADMN')
def new_memo_template(request):
    person = get_object_or_404(Person, find_userid_or_emplid(request.user.username))   
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        form = MemoTemplateForm(request.POST)
        form.fields['unit'].choices = unit_choices 
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person           
            f.save()
            messages.success(request, "Created new memo template %s for %s." % (form.instance.label, form.instance.unit))          
            return HttpResponseRedirect(reverse(memo_templates))
    else:
        form = MemoTemplateForm()
        form.fields['unit'].choices = unit_choices 

    page_title = 'New Memo Template'  
    crumb = 'New'
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               }
    return render(request, 'faculty/new_memo_template.html', context)

@requires_role('ADMN')
def manage_memo_template(request, slug):
    person = get_object_or_404(Person, find_userid_or_emplid(request.user.username))   
    unit_choices = [(u.id, u.name) for u in request.units]    
    memo_template = get_object_or_404(MemoTemplate, slug=slug)
    if request.method == 'POST':
        form = MemoTemplateForm(request.POST, instance=memo_template)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person            
            f.save()
            messages.success(request, "Updated %s letter for %s." % (form.instance.label, form.instance.unit))           
            return HttpResponseRedirect(reverse(memo_templates))
    else:
        form = MemoTemplateForm(instance=memo_template)
        form.fields['unit'].choices = unit_choices 

    page_title = 'Manage Memo Template'  
    crumb = 'Manage' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               'memo_template' : memo_template,
               }
    return render(request, 'faculty/manage_memo_template.html', context)

