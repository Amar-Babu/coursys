from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib import messages
from ra.models import RAAppointment, Project, Account
from ra.forms import RAForm, RASearchForm, AccountForm, ProjectForm
from grad.forms import possible_supervisors
from coredata.models import Member, Person, Role, Unit, Semester
from courselib.auth import requires_role, ForbiddenResponse
from django.template import RequestContext
from datetime import date, timedelta
from grad.models import Scholarship, ScholarshipType
from dashboard.letters import ra_form, OfficialLetter, LetterContents
import json

#This is the search function that that returns a list of RA Appointments related to the query.
@requires_role("FUND")
def search(request, student_id=None):
    if student_id:
        student = get_object_or_404(Person, id=student_id)
    else:
        student = None
    if request.method == 'POST':
        form = RASearchForm(request.POST)
        if not form.is_valid():
            messages.add_message(request, messages.ERROR, 'Invalid search')
            context = {'form': form}
            return render_to_response('ra/search.html', context, context_instance=RequestContext(request))
        search = form.cleaned_data['search']
        return HttpResponseRedirect(reverse('ra.views.student_appointments', kwargs={'userid': search.userid}))
    if student_id:
        form = RASearchForm(instance=student, initial={'student': student.userid})
    else:
        form = RASearchForm()
    context = {'form': form}
    return render_to_response('ra/search.html', context, context_instance=RequestContext(request))

#This is an index of all RA Appointments belonging to a given person.
@requires_role("FUND")
def student_appointments(request, userid):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    appointments = RAAppointment.objects.filter(person__userid=userid, unit__id__in=depts).order_by("-created_at")
    student = Person.objects.get(userid=userid)
    return render(request, 'ra/student_appointments.html', {'appointments': appointments, 'student': student}, context_instance=RequestContext(request))

#A helper method to determine the number of pay periods between two dates.
def pay_periods(start_date, end_date):
    weekdays = 0
    while start_date <= end_date:
        if start_date.weekday() != 5 and start_date.weekday() != 6:
            weekdays += 1
        start_date += timedelta(days=1)
    return float(weekdays)/10

#New RA Appointment
@requires_role("FUND")
def new(request):
    if request.method == 'POST':
        raform = RAForm(request.POST)
        if raform.is_valid():
            userid = raform.cleaned_data['person'].userid
            appointment = raform.save()
            messages.success(request, 'Created RA Appointment for ' + appointment.person.first_name + " " + appointment.person.last_name)
            return HttpResponseRedirect(reverse(student_appointments, kwargs=({'userid': userid})))
    else:
        semester = Semester.first_relevant() 
        periods = str(pay_periods(semester.start, semester.end))
        raform = RAForm(initial={'start_date': semester.start, 'end_date': semester.end, 'pay_periods': periods, 'hours': 70 })
        raform.fields['scholarship'].choices=[("", "---------")]
        raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
        raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
        raform.fields['project'].choices = [(p.id, unicode(p.project_number)) for p in Project.objects.filter(unit__in=request.units)]
        raform.fields['account'].choices = [(a.id, u'%s (%s)' % (a.account_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    return render(request, 'ra/new.html', { 'raform': raform })

#New RA Appointment with student pre-filled.
@requires_role("FUND")
def new_student(request, userid):
    semester = Semester.first_relevant() 
    periods = str(pay_periods(semester.start, semester.end))
    raform = RAForm(initial={'person': userid, 'start_date': semester.start, 'end_date': semester.end, 'pay_periods': periods, 'hours': 70 })
    raform.fields['scholarship'].choices=[("", "---------")]
    raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
    raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    raform.fields['project'].choices = [(p.id, unicode(p.project_number)) for p in Project.objects.filter(unit__in=request.units)]
    raform.fields['account'].choices = [(a.id, u'%s (%s)' % (a.account_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    person = Person.objects.get(emplid=userid)
    return render(request, 'ra/new.html', { 'raform': raform, 'person': person })

#Edit RA Appointment
@requires_role("FUND")
def edit(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)    
    if request.method == 'POST':
        raform = RAForm(request.POST, instance=appointment)
        if raform.is_valid():
            userid = raform.cleaned_data['person'].userid
            raform.save()
            messages.success(request, 'Updated RA Appointment for ' + appointment.person.first_name + " " + appointment.person.last_name)
            return HttpResponseRedirect(reverse(student_appointments, kwargs=({'userid': userid})))
    else:
        #The initial value needs to be the person's emplid in the form. Django defaults to the pk, which is not human readable.
        raform = RAForm(instance=appointment, initial={'person': appointment.person.emplid})
        #As in the new method, choices are restricted to relevant options.
        raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
        scholarship_choices = [("", "---------")]
        for s in Scholarship.objects.filter(student__person__emplid = appointment.person.emplid):
            scholarship_choices.append((s.pk, s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"))
        raform.fields['scholarship'].choices = scholarship_choices
        raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
        raform.fields['project'].choices = [(p.id, unicode(p.project_number)) for p in Project.objects.filter(unit__in=request.units)]
        raform.fields['account'].choices = [(a.id, u'%s (%s)' % (a.account_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    return render(request, 'ra/edit.html', { 'raform': raform, 'appointment': appointment })

#Quick Reappoint, The difference between this and edit is that the reappointment box is automatically checked, and date information is filled out as if a new appointment is being created.
#Since all reappointments will be new appointments, no post method is present, rather the new appointment template is rendered with the existing data which will call the new method above when posting.
@requires_role("FUND")
def reappoint(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)    
    semester = Semester.first_relevant()
    periods = str(pay_periods(semester.start, semester.end))
    raform = RAForm(instance=appointment, initial={'person': appointment.person.emplid, 'reappointment': True, 'start_date': semester.start, 'end_date': semester.end, 'pay_periods': periods, 'hours': 70 })
    raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
    scholarship_choices = [("", "---------")]
    for s in Scholarship.objects.filter(student__person__emplid = appointment.person.emplid):
            scholarship_choices.append((s.pk, s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"))
    raform.fields['scholarship'].choices = scholarship_choices
    raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    raform.fields['project'].choices = [(p.id, unicode(p.project_number)) for p in Project.objects.filter(unit__in=request.units)]
    raform.fields['account'].choices = [(a.id, u'%s (%s)' % (a.account_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    return render(request, 'ra/new.html', { 'raform': raform, 'appointment': appointment })

#View RA Appointment
@requires_role("FUND")
def view(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    student = Person.objects.get(userid=appointment.person.userid)
    return render(request, 'ra/view.html', {'appointment': appointment, 'student': student}, context_instance=RequestContext(request))

#View RA Appointment Form (PDF)
@requires_role("FUND")
def form(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s.pdf' % (appointment.slug)
    ra_form(appointment, response)
    return response

@requires_role("FUND")
def letter(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s-letter.pdf' % (appointment.slug)
    letter = OfficialLetter(response, unit=appointment.unit)
    contents = LetterContents(
        to_addr_lines=[], 
        from_name_lines=[appointment.hiring_faculty.first_name + " " + appointment.hiring_faculty.last_name,        appointment.unit.name], 
        salutation="Dear " + appointment.person.first_name, 
        closing="Yours Truly", 
        signer=appointment.hiring_faculty,
        cosigner_lines=['I agree to the conditions of employment', appointment.person.first_name + " " + appointment.person.last_name])
    paragraphs = [
        """This is to confirm remuneration of work performed as a Research Assistant from """ + appointment.start_date.strftime("%B %d, %y") +  """ to """  + appointment.end_date.strftime("%B %d, %y") + """, will be a Lump Sum payment of $""" + str(appointment.lump_sum_pay) + """.""",
        """Termination of this appointment may be initiated by either party giving one (1) week notice, except in the case of termination for cause.""",
        """This contract of employment exists solely between myself as recipient of research grant funds and your self. In no manner of form does this employment relationship extend to or affect Simon Fraser University in any way.""",
        """The primary purpose of this appointment is to assist you in furthering your education and the pursuit of your degree through the performance of research activities in your field of study. As such, payment for these activities will be classified as scholarship income for taxation purposes. Accordingly, there will be no income tax, CPP or EI deductions from income. You should set aside funds to cover your eventual income tax obligation; note that the first $3K total annual income from scholarship sources is not taxable.""",
        """Basic Benefits: further details are in SFU Policies and Procedures R 50.02, which can be found on the SFU website.""",
        """If you accept the terms of this appointment, please sign and return the enclosed copy of this letter, retaining the original for your records.""",
    ]
    contents.add_paragraphs(paragraphs)
    letter.add_letter(contents)
    letter.write()
    return response


#Methods relating to Account creation. These are all straight forward.
@requires_role("FUND")
def new_account(request):
    accountform = AccountForm(request.POST or None)
    #This restricts a user to only creating account for a unit to which they belong.
    accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if accountform.is_valid():
            account = accountform.save()
            messages.success(request, 'Created account ' + str(account.account_number))
            return HttpResponseRedirect(reverse('ra.views.accounts_index'))
    return render(request, 'ra/new_account.html', {'accountform': accountform})

@requires_role("FUND")
def accounts_index(request):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    accounts = Account.objects.filter(unit__id__in=depts).order_by("account_number")
    return render(request, 'ra/accounts_index.html', {'accounts': accounts}, context_instance=RequestContext(request))

@requires_role("FUND")
def delete_account(request, account_slug):
    account = get_object_or_404(Account, slug=account_slug)
    messages.success(request, 'Deleted account ' + str(account.account_number))
    account.delete()
    return HttpResponseRedirect(reverse(accounts_index))

@requires_role("FUND")
def edit_account(request, account_slug):
    account = get_object_or_404(Account, slug=account_slug)
    if request.method == 'POST':
        accountform = AccountForm(request.POST, instance=account)
        if accountform.is_valid():
            accountform.save()
            messages.success(request, 'Updated account ' + str(account.account_number))
            return HttpResponseRedirect(reverse(accounts_index))
    else:
        accountform = AccountForm(instance=account)
        accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    return render(request, 'ra/edit_account.html', {'accountform': accountform, 'account': account}, context_instance=RequestContext(request))

#Project methods. Also straight forward.
@requires_role("FUND")
def new_project(request):
    projectform = ProjectForm(request.POST or None)
    #Again, the user should only be able to create projects for units that they belong to.
    projectform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if projectform.is_valid():
            project = projectform.save()
            messages.success(request, 'Created project ' + str(project.project_number))
            return HttpResponseRedirect(reverse('ra.views.projects_index'))
    return render(request, 'ra/new_project.html', {'projectform': projectform})

@requires_role("FUND")
def projects_index(request):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    projects = Project.objects.filter(unit__id__in=depts).order_by("project_number")
    return render(request, 'ra/projects_index.html', {'projects': projects}, context_instance=RequestContext(request))

@requires_role("FUND")
def delete_project(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    messages.success(request, 'Deleted project ' + str(project.project_number))
    project.delete()
    return HttpResponseRedirect(reverse(projects_index))

@requires_role("FUND")
def edit_project(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    if request.method == 'POST':
        projectform = ProjectForm(request.POST, instance=project)
        if projectform.is_valid():
            projectform.save()
            messages.success(request, 'Updated project ' + str(project.project_number))
            return HttpResponseRedirect(reverse(projects_index))
    else:
        projectform = ProjectForm(instance=project)
        projectform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    return render(request, 'ra/edit_project.html', {'projectform': projectform, 'project': project}, context_instance=RequestContext(request))

@requires_role("FUND")
def search_scholarships_by_student(request, student_id):
    #check permissions
    roles = Role.all_roles(request.user.username)
    allowed = set(['FUND'])
    if not (roles & allowed):
        return ForbiddenResponse(request, "Not permitted to search scholarships by student.")
    scholarships = Scholarship.objects.filter(student__person__emplid=student_id)
    response = HttpResponse(mimetype="application/json")
    data = [{'value': s.pk, 'display': s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"}  for s in scholarships]
    json.dump(data, response, indent=1)
    return response
