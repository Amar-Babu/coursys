from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import *
from coredata.models import Person, Role, Unit, Semester, CAMPUS_CHOICES
from django.template import RequestContext
from django import forms
from django.forms.models import modelformset_factory, inlineformset_factory
from courselib.auth import *
from django.core import serializers
from django.utils.safestring import mark_safe
import datetime
from django.forms.formsets import formset_factory
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage,\
    InvalidPage

# get semester based on input datetime. defaults to today
# returns semseter object
def get_semester(date=datetime.date.today()):
    year = date.year
    next_sem = 0
    for s in Semester.objects.filter(start__year=year).order_by('-start'):
        if next_sem == 1:
            # take this semster
            return s
        if date > s.start:
            if date < s.end :
                return s
            else:
                #take the next semseter
                next_sem = 1

@requires_role("GRAD")
def index(request):
    grads = GradStudent.objects.all()
    paginator = Paginator(grads, 5)
    
    try: 
        p = int(request.GET.get("page", '1'))
    except ValueError: p = 1

    try:
        grads = paginator.page(p)
    except (InvalidPage, EmptyPage):
        grads = paginator.page(paginator.num_pages)    
    
    # set frontend defaults
    page_title = 'Graduate Student Records'  
    crumb = 'Grads' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'grads': grads               
               }
    return render(request, 'grad/index.html', context)


@requires_role("GRAD")
def view_all(request, grad_slug):
    # will display academic, personal, FIN, status history, supervisor
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    supervisors = Supervisor.objects.filter(student=grad, position=1)# show the main supervisor (position = 1)
    status = get_list_or_404(GradStatus, student=grad)
    
    #calculate missing reqs
    completed_req = CompletedRequirement.objects.filter(student=grad)
    req = GradRequirement.objects.filter(program=grad.program)
    missing_req = req    
    for s in completed_req:
        missing_req = missing_req.exclude(description=s.requirement.description)
    #get_list_or_404(CompletedRequirement, student=grad)
    
    # set frontend defaults
    page_title = "%s 's Graduate Student Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)

    gp = grad.person.get_fields
    gs = [s.get_fields for s in status]
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               'gs' : gs,
               'supervisors' : supervisors,
               'completed_req' : completed_req,               
               'missing_req' : missing_req         
               }
    return render(request, 'grad/view_all.html', context)


@requires_role("GRAD")
def manage_supervisors(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    supervisors = Supervisor.objects.filter(student=grad, position__gte=1)
    # Using filter because get returns an error when there are no matching queries
    pot_supervisor = Supervisor.objects.filter(student=grad, position=0) 
    # Initialize potential supervisor to first on of the list of results
    # There should be exactly one match unless there is data error
    extra_form = 0
    if(supervisors.count()==0):
        extra_form = 1
    if (pot_supervisor.count() == 0):
        pot_supervisor = None
    else:
        pot_supervisor = pot_supervisor[0]
        
    supervisors_formset = modelformset_factory(Supervisor, form=SupervisorForm, extra=extra_form, max_num=4)(queryset=supervisors)
    for f in supervisors_formset:
        f.fields['supervisor'].choices = possible_supervisors([grad.program.unit])
        #f.fields['position'].widget = forms.HiddenInput()
        if(extra_form==1):
            print f.fields['position'].initial
            f.fields['position'].initial = 1

    if request.method == 'POST':
        potential_supervisors_form = PotentialSupervisorForm(request.POST, instance=pot_supervisor, prefix="pot_sup")
        if potential_supervisors_form.is_valid():
            superF = potential_supervisors_form.save(commit=False)
            superF.modified_by = request.user.username
            superF.student = grad #Passing grad student info to model
            superF.position = 0   #Hard coding potential supervisor and passing to model
            superF.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug} ))
    else:
        potential_supervisors_form = PotentialSupervisorForm(instance=pot_supervisor, prefix="pot_sup")
        potential_supervisors_form.fields['supervisor'].choices = \
                possible_supervisors([grad.program.unit])

    # set frontend defaults
    page_title = "%s's Supervisor(s) Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    context = {
               'supervisors_formset': supervisors_formset,
               'potential_supervisors_form': potential_supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               'supervisors' : supervisors,
               }
    return render(request, 'grad/manage_supervisors.html', context)

@requires_role("GRAD")
def update_supervisors(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    if request.method == 'POST':
        supervisors_formset = modelformset_factory(Supervisor, form=SupervisorForm, max_num=4)
        modelformset = supervisors_formset(request.POST)
        print modelformset.is_valid()
        print "---"
        if modelformset.is_valid():
            
            temp = modelformset.save(commit=False)
            for entry in temp:
                entry.student = grad
            modelformset.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug} ))
        else:
            return HttpResponseRedirect(reverse(manage_supervisors, kwargs={'grad_slug':grad_slug}))

    else:
        return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug': grad_slug}))

@requires_role("GRAD")
def manage_requirements(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)    
    
    #calculate/find missing reqs
    completed_req = CompletedRequirement.objects.filter(student=grad)
    req = GradRequirement.objects.filter(program=grad.program)
    missing_req = req    
    for s in completed_req:
        missing_req = missing_req.exclude(description=s.requirement.description)
    num_missing = req.count()
    
    ReqFormSet = inlineformset_factory(GradStudent, CompletedRequirement, max_num=num_missing, can_order=False) 
    if request.method == 'POST':
        req_formset = ReqFormSet(request.POST, request.FILES, instance=grad, prefix='req')        
        if req_formset.is_valid():
            req_formset.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug} ))
    else:
        req_formset = ReqFormSet(instance=grad,  prefix='req')

    # set frontend defaults
    page_title = "%s's Requirements Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields     
    context = {
               #'req_form': req_form,
               'req_formset': req_formset,
               'page_title' : page_title,
               'crumb' : crumb,
               'gp' : gp,
               'grad' : grad,
               'missing_req' : missing_req     
               }
    return render(request, 'grad/manage_requirements.html', context)


@requires_role("GRAD")
def manage_academics(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    
    if request.method == 'POST':
        grad_form = GradAcademicForm(request.POST, instance=grad, prefix="grad")
        if grad_form.is_valid():
            gradF = grad_form.save(commit=False)
            gradF.modified_by = request.user.username
            grad.slug = None
            gradF.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad.slug} ))
    else:
        grad_form = GradAcademicForm(instance=grad, prefix="grad")

    # set frontend defaults
    page_title = "%s 's Graduate Academic Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    context = {
               'grad_form': grad_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,        
               }
    return render(request, 'grad/manage_academics.html', context)


@requires_role("GRAD")
def manage_status(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    gs = get_list_or_404(GradStatus, student=grad)
    status = gs[0]

    if request.method == 'POST':
        status_form = GradStatusForm(request.POST, instance=status, prefix="stat")
        if status_form.is_valid():
            status_form.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug} ))
    else:
        status_form = GradStatusForm(instance=status, prefix="stat")

    # set frontend defaults
    page_title = "%s 's Status Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields
    gs = [s.get_fields for s in gs]
    status = status.get_fields
    context = {
               'status_form': status_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               'gs' : gs,
               'status' : status
               }
    return render(request, 'grad/manage_status.html', context)
    
@requires_role("GRAD")
def new(request):
    if request.method == 'POST':
        grad_form = GradStudentForm(request.POST, prefix="grad")
        #req_form = CompletedRequirementForm(request.POST, prefix="req")
        supervisors_form = PotentialSupervisorForm(request.POST, prefix="sup")
        status_form = GradStatusForm(request.POST, prefix="stat")
        if grad_form.is_valid() and supervisors_form.is_valid() and status_form.is_valid() :
            gradF = grad_form.save(commit=False)
            gradF.created_by = request.user.username
            gradF.save()
            #reqF = req_form.save(commit=False)
            #req_form.cleaned_data["student"] = gradF
            #reqF.student_id = gradF.id
            #req_form.save()
            superF = supervisors_form.save(commit=False)
            supervisors_form.cleaned_data["student"] = gradF
            superF.student_id = gradF.id
            superF.position = 0
            superF.created_by = request.user.username
            supervisors_form.save()
            statusF = status_form.save(commit=False)
            status_form.cleaned_data["student"] = gradF
            statusF.created_by = request.user.username
            statusF.student_id = gradF.id
            status_form.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':gradF.slug} ))
    else:
        #req_list = get_list_or_404(GradRequirement)
        prog_list = get_list_or_404(GradProgram)
        grad_form = GradStudentForm(prefix="grad", initial={'program': prog_list[0], 'campus': CAMPUS_CHOICES[0][0] })
        #req_form = CompletedRequirementForm(prefix="req", initial={'semester': get_semester(), 'requirement': req_list[0]})
        supervisors_form = PotentialSupervisorForm(prefix="sup",)  
        status_form = GradStatusForm(prefix="stat", initial={'status': 'ACTI', 'start': get_semester() })  
        #initial: 'start' returns nothing if there are no future semester available in DB 

    # set frontend defaults
    page_title = 'New Graduate Student Record'
    crumb = 'New Grad' 
    context = {
               'grad_form': grad_form,
               #'req_form': req_form,
               'supervisors_form': supervisors_form,
               'status_form': status_form,               
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new.html', context)

############################################################
# temporary for adding new programs
@requires_role("GRAD")
def new_program(request):
    if request.method == 'POST':
        form = GradProgramForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(programs))
    else:
        form = GradProgramForm(initial={'unit': 2})     

    page_title = 'New Program'  
    crumb = 'New Program' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new_program.html', context)

@requires_role("GRAD")
def programs(request):
    programs = GradProgram.objects.all()
    
    # set frontend defaults
    page_title = 'Graduate Programs Records'
    crumb = 'Grad Programs' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'programs': programs               
               }
    return render(request, 'grad/programs.html', context)

@requires_role("GRAD")
def requirements(request):
    requirements = GradRequirement.objects.all()
    paginator = Paginator(requirements, 5)
    
    try: 
        req = int(request.GET.get("page", '1'))
    except ValueError: req = 1

    try:
        requirements = paginator.page(req)
    except (InvalidPage, EmptyPage):
        requirements = paginator.page(paginator.num_pages)
    
    page_title = 'Graduate Requirements'
    crumb = 'Grad Requirements'     
    context = {
               'req' : req,
               'page_title' : page_title,
               'crumb' : crumb,
               'requirements': requirements                 
               }
    return render(request, 'grad/requirements.html', context)

@requires_role("GRAD")
def new_requirement(request):
    if request.method == 'POST':
        form = GradRequirementForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(requirements))
    else:
        form = GradRequirementForm(initial={'unit': 2})     

    page_title = 'New Requirement'  
    crumb = 'New Requirement' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new_requirement.html', context)

# End of Temp
#############################################################
